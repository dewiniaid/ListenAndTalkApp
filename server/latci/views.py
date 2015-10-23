import bottle
from bottle import route, request, response
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
from latci.api.references import ScalarReferenceManager
import latci.api.errors as err

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
        super().__init__(names, bases, dct)
        _classes_to_init.add(cls)


class StopDispatch(Exception):
    """
    Used to abort the current dispatch() invocation and immediately bail with any current errors.
    """
    pass


class FixMeError(Exception):
    """
    Exception for things that are exceptional but ought to be handled differently.  Placeholder.
    """
    pass


class RESTController(metaclass=RESTMeta):
    """
    Unified REST Request Manager for a single object.

    :cvar url_prefix: Used for autogenerating URLs in setup() in subclasses.  e.g. /api/v2/
    :cvar url_base: Base URL for routes, e.g. /api/v2/object
    :cvar url_instance: URL suffix for routes that refer to a single object, e.g. <key>.  A leading slash is
        automatically added.
    :cvar name: Name of this resource.  Used for error handling and URL generation.
    :cvar model: Corresponding SQLAlchemy model.
    :cvar bulk_max: Maximum amount of entities allowed in a bulk operation.  None = no limit.
    :cvar manager: ReferenceManager for this object.  Created by create_manager() if None.
    :cvar allow_delete: Allow instances to be deleted. Enables per-item DELETE.
    :cvar allow_delete_all: Allow the entire collection to be deleted. Requires allow_delete.
    :cvar allow_create: Allow instances to be created. Enables per-collection POST.
    :cvar allow_update: Allow instances to be updated. Enables per-item PATCH.
    :cvar allow_replace: Allow instances to be replaced. Enables per-item PUT.
    :cvar allow_replace_all: Allow the entire collection to be replaced. Requires allow_replace.
    :cvar allow_patch_create: Allow instances to be created as part of a bulk update by specifying a null reference
        and all required fields. Ignored if allow_create is False
    :cvar allow_patch_delete: Allow instances to be deleted as part of a bulk update by specifying a reference and
        updating its value to null. Ignored if allow_delete is False.
    :cvar treat_put_as_patch: Treat PUT as PATCH if allow_replace is False.
    :cvar SchemaClass: Marshmallow Schema for process_in/process_out
    :ivar db: Database session
    :ivar method: Bottle request method being used.
    :ivar errors: List of accumulated errors.  If this list is not empty, dispatch() will return an appropriate error
        and rollback the transaction rather than allowing any modifications.
    :ivar options: Dictionary of possible options.
    :ivar auth: Authentication session information
    """
    url_prefix = '/api/v2/'
    url_base = None
    url_instance = '<key:int>'

    model = None
    bulk_max = None
    manager = None
    create_manager = None
    name = None

    allow_fetch = True
    allow_delete = False
    allow_create = False
    allow_update = False
    allow_replace = False
    allow_replace_all = False
    allow_patch_create = False
    allow_patch_delete = False
    treat_put_as_patch = True

    SchemaClass = None

    @classmethod
    def item_methods(cls):
        return set(
            x[0]
            for x in (
                ('GET', cls.allow_fetch),
                ('POST', False),
                ('PATCH', cls.allow_update),
                ('PUT', cls.allow_replace or (cls.allow_update and cls.treat_put_as_patch)),
                ('DELETE', cls.allow_delete)
            ) if x[1]
        )

    @classmethod
    def collection_methods(cls):
        return set(
            x[0]
            for x in (
                ('GET', cls.allow_fetch),
                ('POST', cls.allow_create),
                ('PATCH', cls.allow_update),
                ('PUT', (cls.allow_replace and cls.allow_replace_all) or (cls.allow_update and cls.treat_put_as_patch)),
                ('DELETE', cls.allow_delete and cls.allow_delete_all)
            ) if x[1]
        )

    @classmethod
    def get_payload(cls, method, ref, params):
        """
        Returns the incoming JSON payload, after basic validation.  Complains loudly if validation fails.
        :param method: Request method
        :param ref: Instance reference.
        :param params: Possible route arguments.
        :return: Adapted payload.  Or an exception...
        """
        payload = bottle.request.json
        if method in ('GET', 'DELETE'):
            if payload is not None:
                raise err.JSONValidationError('JSON Body is not expected here.')
            payload = {}
        else:
            if payload is None:
                raise err.JSONValidationError('JSON Body is expected here.')
            if not is_dict(payload):
                raise err.JSONValidationError('JSON Body is not in the expected format.')
        return payload

    @classmethod
    def get_options(cls, method, payload):
        """
        Returns incoming options
        :param method: Request method
        :param payload: Parsed payload.
        :return: Options dictionary.
        """
        options = payload.get('options', None)
        if not is_dict(options):
            options = {}

        json = bottle.request.query.get('options', None)
        if json is not None:
            try:
                query_options = latci.json.loads(options)
            except Exception:
                raise err.JSONValidationError("Error in parsing options parameter.")
            if not is_dict(query_options):
                raise err.JSONValidationError("Options parameter must be a dictionary.")
            options.update(query_options)
        return options

    @classmethod
    def get_data(cls, method, payload, ref, params):
        """
        Returns incoming data, after basic validation and transformation.  This includes manufacturing data for
        certain kinds of requests to simplify coding.
        :param method: Request method.
        :param payload: Parsed payload.
        :param ref: Instance reference.
        :param params: Route parameters dictionary.
        :return: Adapted data.  Or an exception
        """
        if method in ('GET', 'DELETE'):
            if ref is None:
                data = None
            else:
                data = ref.to_dict()
            return data
        data = payload.get('data')

        if not (is_dict(data) or (ref is None and is_list(data))):
            raise err.JSONValidationError("Data is in an invalid format.")

        if method == 'POST':
            _transform = lambda _item, _name=cls.name: {
                'value': _item,
                'type': _name,
                'key': None,
                'ref': None
            }
            if is_list(data):
                return [_transform(item) for item in data]
            else:
                return _transform(data)

        for item in listify(data):
            # See if the item is valid.
            if item.get('key') is None:
                if not (method == 'PATCH' and cls.allow_patch_create and cls.allow_create):
                    # Must have a key, unless we're patching and patch is allowed to create new items.
                    raise err.MissingKeyError()
                item['ref'] = None
            else:
                item['ref'] = cls.manager.from_dict(item)

            value = item.setdefault('value', None)
            if (
                    not is_dict(value) and
                    not (ref and value is None and method == 'PATCH' and cls.allow_patch_delete and cls.allow_delete)
            ):
                raise err.MissingValueError(item['ref'])
        return data

    @classmethod
    def dispatch(cls, db=None, key=None, auth=None, **params):
        """
        Dispatches an incoming request.

        Performs sanity checking on incoming data, creates an instance of this class, and then calls that instance.

        :param db: Database session (form Bottle)
        :param auth: Authentication info (from Bottle)
        :param args: Arguments from Bottle
        :param params: Bottle route parameters
        :return: Result of calling the instance, or appropriate error information.
        """
        try:
            if key is None:
                ref = None
            else:
                ref = cls.manager.from_key(key)

            method = bottle.request.method

            if (
                    method == 'PUT' and cls.treat_put_as_patch and not cls.allow_replace and
                    (ref or not cls.allow_replace_all)
            ):
                method = 'PATCH'

            payload = cls.get_payload(method, ref, params)
            options = cls.get_options(method, payload)
            data = cls.get_data(method, payload, ref, params)

            instance = cls(db, options, auth=auth)
            try:
                rv = instance(request.method, ref, data, params)
            except StopDispatch:
                pass
            except err.APIError as ex:
                db.rollback()
                response.status = ex.status
                instance.errors.append(ex)
                return {'errors': instance.errors}
        except err.APIError as ex:
            response.status = ex.status
            return {'errors': [ex]}
        if instance.errors:
            db.rollback()
            response.status = http.client.BAD_REQUEST
            return {'errors': instance.errors}
        return rv

    @classmethod
    def setup(cls):
        """
        Handles one-time class setup tasks.
        """
        # Calculate URLs.
        if cls.url_base is None and cls.url_prefix is not None and cls.name is not None:
            cls.url_base = cls.url_prefix + cls.name
        if not cls.url_base:
            return

        # Setup dispatch callback
        callback = auth_wrapper(keyword='auth', fn=cls.dispatch)
        callback = latci.misc.wrap_exceptions(callback)

        # Build routes
        bottle.route(cls.url_base, cls.collection_methods(), callback=callback)
        bottle.route(cls.url_base + '/' + cls.url_instance, cls.item_methods(), callback=callback)

        # Setup reference manager.
        if cls.manager is None and cls.create_manager is not None:
            cls.manager = cls.create_manager()

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
        self.schema = self.get_schema()

    def __call__(self, method, ref, data, params):
        """
        Handles the second phase of dispatching.
        :param method: Request method
        :param ref: Reference
        :param data: Processed payload data
        :param params: Route parameters.
        :return: JSON response
        """
        if method == 'GET':
            return self.get(ref, params)
        if method == 'DELETE':
            return self.delete(ref, params)
        if method == 'PUT':
            return self.put(ref, params, data)
        return self.patch(ref, params, data)

    def query(self, ref, params):
        """
        Builds an SQL Query, possibly limited to a single instance of our object.

        :param ref: Primary key reference.
        """
        query = self.db.query(self.model)
        if ref is not None:
            query = query.filter(ref.sql_equals())
        return self.query_options(query, ref, params)

    def query_options(self, query, ref, params):
        """
        Modifies query based on any set options.
        :param query: Input query
        :return: Modified query.
        """
        return query

    def get_query_options(self, query, ref, params):
        """
        Modifies query based on options, but only during a fetch.  Applies after query_options()

        Use this function when making query alterations that are only relevant for data being returned.

        The default implementation handles the "limit" and "offset" options.

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

    def get_query(self, ref, params):
        """
        Shorthand for get_query_options(query(ref), ref)
        :param ref:
        :return: Query
        """
        return self.get_query_options(self.query(ref, params), ref, params)

    def get(self, ref, params):
        """
        Called for GET requests.
        """
        print(repr(ref))
        query = self.get_query(ref, params)

        if ref:
            try:
                result = query.one()
            except orm.exc.NoResultFound:
                bottle.abort(404)
            return {'data': self.process_out(result)}
        else:
            return {'data': [self.process_out(row) for row in query]}

    def delete_query_options(self, query, ref, params):
        """
        Modifies query based on options, but only during a delete.  Applies after query_options()

        The default implementation is a no-op, e.g. it returns query unmodified.

        :param query: Input query
        :return: Modified query.
        """
        return query

    def delete_query(self, ref, params):
        """
        Shorthand for get_query_options(query(ref), ref)
        :param ref:
        :return: Query
        """
        return self.delete_query_options(self.query(ref, params), ref, params)

    def delete(self, ref, params):
        """
        Called for DELETE requests.
        """
        query = self.delete_query(ref, params)
        if self.options.get('quiet'):
            count = query.delete()
            response.status = http.client.NO_CONTENT if count else http.client.NOT_FOUND
            self.db.commit()
            return None

        data = []
        for row in query:
            data.append(
                self.manager.from_model(row).to_dict({'value': None}, with_url=False)
            )
            self.db.delete(row)
        if not data:
            raise err.NotFoundError()
        self.db.commit()
        if ref:
            return {'data': data[0]}
        else:
            return {'data': data}

    def put(self, ref, params, data):
        """
        Called for PUT requests (those that aren't... patched... to PATCH.
        :param ref:
        :param params:
        :return:
        """
        raise NotImplementedError("PUT is not implemented.")

    def patch(self, ref, params, data):
        """
        Called for PATCH and POST requests.
        :param ref:
        :param params:
        :return:
        """
        # Remember whether data was a list or not so our return can match it.
        data = listify(data)
        rv = []

        must_exist = self.options.get('must-exist', False)  # For deleting.
        for index, item in enumerate(data):
            itemref = item['ref']
            value = item['value']
            if value is None:
                try:
                    rv.append(self.delete_item(itemref))
                except err.NotFoundError as ex:
                    if not must_exist:
                        pass
                    self.errors.append(ex)
                except err.APIError as ex:
                    self.errors.append(ex)
                # Patched-in delete
                q = self.delete_query(itemref, params)
                continue
            try:
                value = self.process_in(itemref, params, value)
                if itemref is None:
                    rv.append(self.insert_item(value))
                else:
                    rv.append(self.update_item(value))
            except err.APIError as ex:
                if ex.ref is None:
                    if itemref is None:
                        ex.ref = {'index': index}
                    else:
                        ex.ref = itemref
                self.errors.append(ex)
        if self.errors:
            raise StopDispatch()
        self.db.commit()
        if not is_list(data):
            return rv[0]
        return rv

    def process_out(self, instance=None, ref=None):
        """
        Formats data for JSON output.  Returns a dictionary or other serializable object.

        This works by passing an instance through self.schema.dump() to perform the actual formatting.

        :param instance: Instance to serialize.  May be None, in which case the serialization process is skipped and
            the 'value' key of the return value will be None/null.
        :param ref: Reference identifying the instance.  May be None, in which case it is detected from the passed
            instance.

        It is an error if both instance and ref are None.
        """
        if ref is None:
            if instance is None:
                raise ValueError('At least one of ref or instance must be non-None.')
            ref = self.manager.from_model(instance)
        if instance is None:
            value = None
        else:
            value = self.schema.dump(instance).data
        return ref.to_dict({'value': value})

    def process_in(self, ref, params, value, instance=None):
        """
        Parses incoming JSON data and applies it to an instance.

        :param ref: A Reference identifying the instance being modified.  May be None.
        :param params: Additional route parameters.
        :param value: Incoming JSON data.
        :param instance: Instance to apply values to.  Optional.
        """

        result = self.schema.load(value, instance=instance)
        if result.errors:
            self.errors.append(err.ValidationError(ref=ref))
        return result.data

    def get_schema(self):
        """
        Returns a new instance of the Schema class.
        """
        return self.SchemaClass()


# noinspection PyAbstractClass
class SortableRESTController(RESTController):
    """
    Adds sorting capability to ModelRESTManager instances.

    :cvar sortable_columns: Dictionary of allowed sortable columns.  Keys correspond to values occuring in
        self.options['sort'], values correspond to columns on the table.  Values other than strings are assumed to be
        a list of multiple columns to sort by.  If more advanced mapping than this is required, override the
        fetch_query_options() method
    """
    sortable_columns = {}

    def get_query_options(self, query, ref, params):
        query = super().get_query_options(query, ref, params)
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


# noinspection PyAbstractClass
class InactiveFilterRESTController(RESTController):
    def query_options(self, query, ref, params):
        query = super().query_options(query, ref, params)
        field = self.model.date_inactive
        inactive = self.options.get('inactive')
        if inactive:
            if inactive == 'only':
                return query.filter(field.isnot(None))
            return query
        return query.filter(field.is_(None))


# noinspection PyAbstractClass
class StudentRestController(SortableRESTController, InactiveFilterRESTController):
    url_prefix = '/api/v2/'
    url_instance = '<key:int>'

    model = models.Student
    name = 'student'

    allow_fetch = True
    allow_delete = False
    allow_create = True
    allow_update = True
    allow_replace = False
    allow_replace_all = False
    allow_patch_create = True
    allow_patch_delete = False
    treat_put_as_patch = True
    sortable_columns = {v: [v] for v in ('name_first', 'name_last', 'id')}

    class SchemaClass(models.Student.SchemaClass):
        pass

    @classmethod
    def create_manager(cls):
        return ScalarReferenceManager.from_controller(cls, column='id')

    def get_schema(self):
        return self.SchemaClass(
            exclude=('id', 'enrollment'),
            dump_only=('date_inactive', 'date_created')
        )



setup_all()
