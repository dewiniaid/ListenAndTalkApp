from bottle import route, request, response
import bottle
from latci.database import models
from latci.auth import auth_wrapper
from sqlalchemy import sql, orm, exc, inspect
from latci.schema import Schema, SchemaOptions
import collections.abc
import latci.misc
from latci import json
import http.client
import functools
import operator
import abc
import latci.api.references

# Tracks a list of classes to initialize after creation.
_classes_to_init = set()

def setup_all():
    for c in _classes_to_init:
        c.setup()
        print(repr(c))
        print(c.url_base)
    _classes_to_init.clear()

# Helper functions to see if something is a list or a dict, but using abstract classes for extensibility.
def is_list(obj):
    """
    Returns True if the passed object is list-like, False otherwise.

    List-like is currently defined as "looks like a collections.abc.Sequence"
    :param obj:
    :return:
    """
    return isinstance(obj, collections.abc.Sequence)


def is_dict(obj):
    """
    Returns True if the passed object is dict-like, False otherwise.

    Dict-like is currently defined as "looks like a collections.abc.Mapping"
    :param obj:
    :return:
    """
    return isinstance(obj, collections.abc.Mapping)


def listify(obj):
    """
    If obj is list-like, returns obj.  Otherwise, returns a single-element list containing obj.  This allows code that
    works with either a list or a single object to be simplified.

    :param obj: Input object
    :return: obj or [obj]
    """
    return obj if is_list(obj) else [obj]


class RESTMeta(type):
    def __init__(cls, names, bases, dct):
        _classes_to_init.add(cls)


class RESTController(metaclass=RESTMeta):
    """
    Unified REST Request Manager for a single object.

    :cvar url_prefix: Used for autogenerating URLs in setup() in subclasses.  e.g. /api/v2/
    :cvar url_base: Base URL for routes, e.g. /api/v2/object
    :cvar url_unique: URL suffix for routes that refer to a single object, e.g. <id:int>.  A leading slash is
        automatically added.
    :cvar collection_allows: String of "CRUD" (or a subset) indicating allowed HTTP methods:
        C = Create (POST)
        R = Request (GET)
        U = Update/Replace (PUT)
        D = Delete (DELETE)
    :cvar instance_allows: String of "CRUD" (or a subset) indicating allowed HTTP methods.  See collection_allows for
        a list.
    :cvar instance_url_name: Name of instance URL
    :cvar collection_url_name: Name of collection URL

    :ivar db: Database session
    :ivar method: Bottle request method being used.
    :ivar errors: List of accumulated errors.  If this list is not empty, dispatch() will return an appropriate error
        and rollback the transaction rather than allowing any modifications.
    :ivar options: Dictionary of possible options.
    :ivar auth: Authentication information

    """
    url_prefix = '/api/v2'
    url_base = None
    url_unique = '<key>'
    method = None
    collection_route_name = None
    instance_route_name = None
    collection_allows = ''
    instance_allows = ''

    REQUEST_METHOD_MAP = {
        'GET': 'R',
        'PUT': 'C',
        'POST': 'U',
        'DELETE': 'D',
    }

    @classmethod
    def getparam(cls, key, default=None):
        """
        Returns the named request parameter after JSON parsing.

        :param key: Request parameter to return
        :param default: Default to return if parameter was not defined.
        :return: Named parameter, or default if the parameter was not defined.

        This looks at the following URL parameters:
        key - Raw JSON, no encoding

        (The implementation may look at other variations of the same URL parameter in the future)
        """
        value = request.query.get(key, None)
        if value is None:
            return value
        return json.loads(value)

    @classmethod
    def dispatch(cls, *args, db=None, key=None, auth=None, **kwargs):
        """
        Dispatches an incoming request.

        Performs sanity checking on incoming data, then initializes an instance of this class, and then calls that
        instance.

        :param db: Database session (form Bottle)
        :param auth: Authentication info (from Bottle)
        :param args: Arguments from Bottle
        :param kwargs: Kwargs from Bottle
        :return: Result of calling the instance, or appropriate error information.
        """

        # Check to see if this method is allowed.
        action = cls.REQUEST_METHOD_MAP.get(request.method)
        if action is None or action not in (cls.collection_allows if key is None else cls.instance_allows):
            bottle.abort(http.client.METHOD_NOT_ALLOWED)

        # We expect a JSON payload on anything other than GET, so see if it's present and well-formed.
        if request.method != 'GET':
            payload = request.json
            if not cls.validate_payload(payload, key):
                response.status = http.client.BAD_REQUEST
                return {'errors': {'ref': None, 'text': 'JSON Payload is missing or invalid.'}}
            if not cls.validate_data(payload.get('data'), key):
                response.status = http.client.BAD_REQUEST
                return {'errors': {'ref': None, 'text': 'JSON data element is missing or invalid.'}}
        else:
            payload = {}

        # Handle options
        if not is_dict(payload.get('options')):
            payload['options'] = {}

        # Since GET shouldn't have a request body, there's no way for it to specify useful things like options that.
        # way.  So instead, we allow it to be specified in the query string.
        request_options = cls.getparam('options', None)
        if request_options is not None:
            payload['options'].update(request_options)

        instance = cls(db, payload['options'], auth=auth)
        fn = getattr(instance, request.method.lower())
        rv = fn(cls.get_ref(key), request.json, kwargs)

        if instance.errors:
            db.rollback()
            response.status = http.client.BAD_REQUEST
            return {'errors': instance.errors}

        return rv

    @classmethod
    def validate_data(cls, data, key):
        # A single dictionary data element is always okay.
        if is_dict(data):
            return True

        # It's the only thing that's okay if we're not a collection, though.
        if key is not None:
            return False

        # A list for a collection is okay, but only if it contains nothing but zero or more dictionaries.
        # (all() returns True for an empty iterable, which is the correct response.)
        return all(is_dict(item) for item in data)

    @classmethod
    def validate_payload(cls, payload, key):
        # Must have a payload, which is a dictionary.
        return is_dict(payload)

    @classmethod
    def setup(cls):
        """
        Handles one-time class setup tasks.
        """
        if not cls.url_base:
            return
        cls.instance_route_name = cls.url_base + '_ALL'
        cls.collection_route_name = cls.url_base + '_ONE'
        callback = auth_wrapper(keyword='auth', fn=cls.dispatch)
        callback = latci.misc.wrap_exceptions(callback)
        bottle.route(cls.url_base, 'ANY', callback, name=cls.instance_route_name)
        if not cls.url_unique:
            return
        bottle.route(cls.url_base + '/' + cls.url_unique, 'ANY', callback, cls.collection_route_name)

    def __init__(self, db, options, auth=None):
        """
        Handles per-request setup tasks.

        :param db: Database session
        :param options: Options dictionary
        :param auth: Authentication information.
        :return:
        """
        self.errors = []
        self.db = db
        self.auth = auth
        self.options = options

    @classmethod
    @abc.abstractmethod
    def get_ref(cls, key):
        raise RuntimeError('This method must be reimplemented in a subclass.')
        pass


class ModelRESTController(RESTController):
    """
    Extends RESTManager with lots of automagic functionality.

    :cvar resource_name: Name of this resource.  Used for error handling and URL generation.
    :cvar model: Corresponding SQLAlchemy model.
    :cvar SchemaClass: Marshmallow Schema class for conversion of non-primary key columns between JSON and native.
    :cvar bulk_max: Maximum amount of entities allowed in a bulk operation.  None = no limit.
    :ivar schema: Instance of schema_class for this object.
    """
    url_prefix = '/api/v2/'
    url_unique = '<key:int>'
    bulk_max = None
    manager = None
    create_manager = None
    resource_name = None

    @classmethod
    def get_ref(cls, key):
        if key is None:
            return None
        return cls.manager.from_key(key)

    @classmethod
    def setup(cls):
        if cls.url_base is None and cls.url_prefix is not None and cls.resource_name is not None:
            cls.url_base = cls.url_prefix + cls.resource_name
        if cls.url_base is None:
            return
        super().setup()
        if cls.manager is None and cls.create_manager is not None:
            cls.manager = cls.create_manager()

    def query(self, ref):
        """
        Builds an SQL Query, possibly limited to a single instance of our object.

        :param ref: Primary key reference.
        """
        query = self.db.query(self.model)
        if ref is not None:
            query = query.filter(ref.sql_equals())
        return self.query_options(query, ref)

    def query_options(self, query, ref):
        """
        Modifies query based on any set options.
        :param query: Input query
        :return: Modified query.
        """
        return query

    def get_query_options(self, query, ref):
        """
        Modifies query based on options, but only during a fetch.  Applies after query_options()

        Use this function when making query alterations that are only relevant for data being returned.

        The default implementation handles the "limit", "offset" and "order" options.

        :param query: Input query
        :return: Modified query.
        """
        if not ref:
            limit = self.options.get('limit')
            offset = self.options.get('offset')
            if limit is not None:
                limit = int(limit)
                if limit < 1:
                    raise ValueError("Limit may not be less than 1.")
                query = query.limit(limit)
            if offset is not None:
                offset = int(offset)
                if offset < 0:
                    raise ValueError("Offset may not be less than 0.")
                query = query.offset(offset)
        return query

    def get_query(self, ref):
        """
        Shorthand for get_query_options(query(ref), ref)
        :param ref:
        :return: Query
        """
        return self.get_query_options(self.query(ref), ref)

    def get(self, ref, payload, kw):
        """
        Called for GET requests.
        """
        print(repr(ref))
        query = self.get_query_options(self.query(ref), ref)

        if ref:
            try:
                result = query.one()
            except orm.exc.NoResultFound:
                bottle.abort(404)
            return {'data': self.process(result)}
        else:
            return {'data': [self.process(row) for row in query]}

    def delete_query_options(self, query):
        """
        Modifies query based on options, but only during a delete.  Applies after query_options()

        The default implementation is a no-op, e.g. it returns query unmodified.

        :param query: Input query
        :return: Modified query.
        """
        return query

    def delete_query(self, ref):
        """
        Shorthand for get_query_options(query(ref), ref)
        :param ref:
        :return: Query
        """
        return self.delete_query_options(self.query(ref), ref)

    def iter_payload(self, ref, payload):
        """
        Parses the 'data' section of the payload and returns it in a somewhat more processed format.  Also validates.
        :param ref: Reference
        :param payload: Payload
        :return:
        """

        data = listify(payload.get('data'))
        for item in data:
            if item.get('type', self.resource_name) != self.resource_name:
                raise ValueError('Type mismatch')  # FIXME: Should be a proper error representation.

            itemref = self.manager.from_dict(item)
            if ref is not None and ref != itemref:
                raise ValueError('Reference mismatch')  # FIXME: Should be a proper error representation.

            # Check to make sure types alig
            yield itemref, item.get('value')





    def delete(self, ref, payload, kw):
        """
        Called for DELETE requests.

        There's a few interesting ways we can handle deletions:

        1. Do we care if the object(s) existed previously or not?  If not, how do we show the list of what existed and
        what didn't?

        Checks 'delete-mode' option:
        - "strict" Fail if any objects are not found.  The full list of missing objects are included in errors.
        - "strict-fast" Fail if any objects are not found.  The first missing object is included in errors.
        - "loose" Always succeed; return list of matched objects.  No errors listed.  Frontend response for cross-
            referencing
        - "loose-fast" Always succeed; return nothing.  Fast response.

        The default is 'strict'.
        """
        payload = listify(payload)
        if self.bulk_max and len(payload) > self.bulk_max:
            self.errors.append({
                'ref': None,
                'text': (
                    "The payload contained too many items for this operation.  The maximum allowed is {}."
                    .format(self.bulk_max)
                )
            })
            return None
        mode = self.options.get('delete-mode', 'strict')
        if mode not in ('strict', 'strict-fast', 'loose', 'loose-fast'):
            self.errors.append({
                'ref': None,
                'text': "Unsupported delete-mode option."
            })
            return None

        if ref is not None:
            if self.manager.from_dict(payload[0]) == ref:












class SortableRESTController(ModelRESTController):
    """
    Adds sorting capability to ModelRESTManager instances.

    :cvar sortable_columns: Dictionary of allowed sortable columns.  Keys correspond to values occuring in
        self.options['sort'], values correspond to columns on the table.  Values other than strings are assumed to be
        a list of multiple columns to sort by.  If more advanced mapping than this is required, override the
        fetch_query_options() method
    """
    sortable_columns = {}

    def get_query_options(self, query, ref):
        query = super().get_query_options(query, ref)
        if ref is not None:
            return query

        order = self.options.get('order')
        if not isinstance(order, list) or not order:
            return query

        seen = set()  # Avoid duplicate application of sort keys
        for item in order:
            desc = (item[0] == '-')
            if desc: item = item[1:]
            if item not in self.sortable_columns:
                continue
            for col in self.sortable_columns[item]:
                if col in seen:
                    continue
                seen.add(col)
                field = getattr(self.model, col)
                if desc: field = field.desc()
                query = query.order_by(field)
        return query


class InactiveFilterRESTController(ModelRESTController):
    def query_options(self, query, ref):
        query = super().query_options(query, ref)
        field = self.model.date_inactive
        inactive = self.options.get('inactive')
        if inactive:
            if inactive == 'only':
                return query.filter(field.isnot(None))
            return query
        return query.filter(field.is_(None))


class StudentRestController(SortableRESTController, InactiveFilterRESTController):
    url_unique = '<key:int>'
    resource_name = 'student'
    collection_allows = 'CRU'
    instance_allows = 'RU'
    model = models.Student
    sortable_columns = {v: [v] for v in ('name_first', 'name_last', 'id')}
    bulk_max = None

    @classmethod
    def create_manager(cls):
        return latci.api.references.ScalarReferenceManager.from_controller(controller=cls, column='id')

    def process(self, obj):
        ref = self.manager.from_model(obj)
        rv = ref.to_dict({'value': obj})
        return rv


setup_all()