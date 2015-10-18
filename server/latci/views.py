from bottle import route, request, response
import bottle
from latci.database import models
from latci.auth import auth_wrapper
from sqlalchemy import sql, orm, exc
from latci.schema import Schema, SchemaOptions
import collections.abc
import latci.misc
from latci import json
import http.client

# Tracks a list of classes to initialize after creation.
_classes_to_init = set()

def setup_all():
    for c in _classes_to_init:
        print(repr(c))
        c.setup()
    _classes_to_init.clear()


class RESTMeta(type):
    def __init__(cls, names, bases, dct):
        _classes_to_init.add(cls)


class RESTManager(metaclass=RESTMeta):
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
    :ivar is_collection: True if this request refers to the entire collection.
    :ivar errors: List of accumulated errors.  If this list is not empty, dispatch() will return an appropriate error
        and rollback the transaction rather than allowing any modifications.
    :ivar options: Dictionary of possible options.
    :ivar auth: Authentication information

    """
    url_prefix = '/api/v2'
    url_base = None
    url_unique = None
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
    def dispatch(cls, db, *args, auth=None, **kwargs):
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

        is_collection = (request.route.name == cls.collection_route_name)
        # Check to see if this method is allowed.
        action = cls.REQUEST_METHOD_MAP.get(request.method)
        if action is None or action not in (cls.collection_allows if is_collection else cls.instance_allows):
            bottle.abort(http.client.METHOD_NOT_ALLOWED)

        # We expect a JSON payload on anything other than GET, so see if it's present and well-formed.
        if request.method != 'GET':
            payload = request.json
            if not cls.validate_payload(payload, is_collection):
                response.status = http.client.BAD_REQUEST
                return {'errors': {'ref': None, 'text': 'JSON Payload is missing or invalid.'}}
            if not cls.validate_data(payload.get('data'), is_collection):
                response.status = http.client.BAD_REQUEST
                return {'errors': {'ref': None, 'text': 'JSON data element is missing or invalid.'}}
        else:
            payload = {}

        # Handle options
        if not isinstance(payload.get('options'), collections.abc.Mapping):
            payload['options'] = {}

        # Since GET shouldn't have a request body, there's no way for it to specify useful things like options that.
        # way.  So instead, we allow it to be specified in the query string.
        request_options = cls.getparam('options', None)
        if request_options is not None:
            payload['options'].update(request_options)

        instance = cls(db, request.method, is_collection, payload['options'], auth)
        rv = instance(request.json, key=kwargs)
        if instance.errors:
            response.status = http.client.BAD_REQUEST
            return {'errors': instance.errors}

        return rv

    @classmethod
    def validate_data(cls, data, is_collection=False):
        is_mapping = isinstance(data, collections.abc.Mapping)
        is_list = isinstance(data, collections.abc.Iterable)

        # A single dictionary data element is always okay.
        if isinstance(data, collections.abc.Mapping):
            return True

        # It's the only thing that's okay if we're not a collection, though.
        if not is_collection:
            return False

        # A list for a collection is okay, but only if it contains nothing but zero or more dictionaries.
        # (all() returns True for an empty iterable, which is the correct response.)
        return all(isinstance(item, collections.abc.Mapping) for item in data)

    @classmethod
    def validate_payload(cls, payload, is_collection=False):
        # Must have a payload, which is a dictionary.
        return isinstance(payload, collections.abc.ABCMapping)

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

    def __init__(self, db, is_collection, options, auth=None):
        """
        Handles per-request setup tasks.

        :param db: Database session
        :param is_collection: True if this request is acting on the entire collection, False for a single item.
        :param options: Options dictionary
        :param auth: Authentication information.
        :return:
        """
        self.errors = []
        self.db = db
        self.is_collection = is_collection
        self.auth = auth
        self.options = options

    def __call__(self, payload, key=None):
        """
        Called to actually service the request.
        :param payload: JSON Payload data
        :param key: Dict representing primary key data.
        :return: JSON Result.
        """
        self.options = payload['options']
        pass


class ModelRESTManager(RESTManager):
    """
    Extends RESTManager with lots of automagic functionality.

    :cvar resource_name: Name of this resource.  Used for error handling and URL generation.
    :cvar primary_keys: Dictionary of primary key info.  Keys correspond to the primary key dictionary, values
        correspond to corresponding columns on the table.  If more advanced mapping than this is required, override the
        get_key(), set_key(), and key_condition() methods.
    :cvar sortable_columns: Dictionary of allowed sortable columns.  Keys correspond to values occuring in
        self.options['sort'], values correspond to columns on the table.  Values other than strings are assumed to be
        a list of multiple columns to sort by.  If more advanced mapping than this is required, override the
        fetch_query_options() method
    :cvar model: Corresponding SQLAlchemy model.
    :cvar SchemaClass: Marshmallow Schema class for conversion of non-primary key columns between JSON and native.
    :ivar schema: Instance of schema_class for this object.
    """
    url_prefix = '/api/v2/
    url_unique = '<id:int>'
    resource_name = 'student'
    collection_allows = 'CRU'
    instance_allows = 'RU'
    model = models.Student
    primary_keys = {v: v for v in ['id']}
    sortable_columns = {v: v for v in ('name_first', 'name_last', 'id')}

    @classmethod
    def setup(cls):
        if cls.url_base is None:
            cls.url_base = cls.url_prefix + cls.resource_name
        return super().setup()

    def get_key(self, obj):
        """
        Retrieves the primary key data from an instance in a form that's consistent with what we receive as URL and
        JSON data.
        :param obj: Instance to retrieve data from
        :return: Dictionary of primary key data
        """
        return {
            k: getattr(instance, v) for k, v in self.primary_keys.items()
        }

    def set_key(self, obj, key):
        """
        Modifies the passed instance to set its primary key columns to match the given key dict.
        JSON data.

        Attributes not in the dictionary are not modified on the instance.  Keys not defined in primary_keys are
        ignored, which allows passing a full JSON data structure to set_key.

        :param obj: Instance to modify data on
        :param key: Primary key dictionary.
        :return: Modified object.
        """
        for k, v in key.items():
            if k not in self.primary_keys: continue
            setattr(obj, self.primary_keys[k], v)
        return obj

    def key_condition(self, key):
        """
        Given a primary key dictionary, return an SQLAlchemy condition that satisfies it when querying SQLAlchemy.
        """
        return sql.and_(
            *[getattr(self.model, self.primary_keys[k]) == key[k] for k, v in key.items() if k in self.primary_keys]
        )

    class SchemaClass(models.Student.SchemaClass):
        class Meta:
            exclude = ['enrollment']

    def __init__(self, db, method, is_collection, auth=None):
        super().__init__(db, method, is_collection, auth)
        self.schema = self.SchemaClass(session=self.db)

    def query(self, key=None):
        """
        Builds an SQL Query, possibly limited to a single instance of our object.

        :param key: Primary key data.  Ignored if we're a collection.
        """
        query = self.db.query(self.model)
        if not self.is_collection:
            query = query.filter(self.key_condition(key))
        return self.query_options(query)

    def query_options(self, query):
        """
        Modifies query based on any set options.
        :param query: Input query
        :return: Modified query.
        """
        return query

    def fetch_query_options(self, query):
        """
        Modifies query based on options, but only during a fetch.  Applies after query_options()

        Use this function when making query alterations that are only relevant for data being returned.

        :param query: Input query
        :return: Modified query.
        """
        if self.is_collection:
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
            order = self.options.get('order')
            if isinstance(order, list):
                seen = set()  # Avoid duplicate application of sort keys
                for item in order:
                    desc = (item[0] == '-')
                    if desc: item = item[1:]
                    if item not in self.sortable_columns:
                        continue
                    for col in self.sortable_columns[item]:
                        if col in seen: continue
                        seen.add(col)
                        field = getattr(self.model, col)
                        if desc: field = field.desc()
                        query = query.order_by(field)
        return query

    def fetch(self, key=None):
        """Called for GET requests."""
        query = self.fetch_query_options(self.query())

        if self.is_collection:
            try:
                result = query.one()
            except orm.exc.NoResultFound:
                bottle.abort(404)
            return {'data': self.process(result)}
        else:
            return {'data': [self.process(row) for row in query]}

    def __call__(self, payload=None, key=None):
        """
        Logic:

        When called, if we're operating as a collection:
            - In Create (POST) mode, we receive a list of JSON objects to create (or a single JSON object)
            - In Update (PUT) mode, we receive the same list -- but they include IDs for existing objects.
            - In Delete (DELETE) mode, we receive the same list -- but they include IDs for existing objects.
            - In Retrieve (GET) mode, we receive no data.

        In non-collection mode:
            - Create has no defined meaning, unless overridden.
            - Update is as in collection mode, but the ID is in the URL
            - Delete is as in collection mode, but the ID is in the URL
            - Retrieve is as in collection mode, but the ID is in the URL
        """


        if request.method != 'GET':
            data = self.reformat_data(payload['data'], key)

        if request.method == 'GET':
            query = db.query(self.model)



