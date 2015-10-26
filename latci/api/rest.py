import collections.abc
import http.client
import functools

import bottle
from bottle import request, response
from sqlalchemy import orm, exc

from latci.auth import auth_wrapper
import latci.misc
import latci.api.errors as err
import collections
from latci import config

import datetime


# Tracks a list of classes to initialize after creation.
_classes_to_init = set()


def setup_all():
    for c in _classes_to_init:
        c.setup()
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


class InstanceCache(collections.UserDict):
    """
    Subclass UserDict to provide a cache of loaded instances.
    """
    _NOT_FOUND = object()

    def __init__(self, query_factory, reference_factory):
        super().__init__()
        self.query_factory = query_factory
        self.reference_factory = reference_factory

    def _key(self, item): return item if isinstance(item, str) else item.to_key()

    def __getitem__(self, item):
        if isinstance(item, str):
            key, ref = item, self.reference_factory.from_key(item)
        else:
            key, ref = item.to_key(), item
        try:
            rv = super().__getitem__(key)
        except KeyError as ex:
            try:
                rv = self.query_factory(ref).one()
            except orm.exc.NoResultFound:
                rv = _NOT_FOUND
            super().__setitem__(key, rv)
        if rv is _NOT_FOUND:
            raise KeyError(key)
        return rv

    def __setitem__(self, item, value): return super().__setitem__(self._key(item), value)

    def __delitem__(self, item): return super().__delitem__(self._key(item))

    def __contains__(self, item):
        rv = super().__contains__(self._key(item))
        return False if rv is self._NOT_FOUND else rv

    def clear(self):
        # UserDict's parent class uses a extremely inefficient (but safe) method for doing this.  Replace it with
        # something faster, since we don't do anything particularly special when removing dict keys.
        self.data = {}

    def add(self, instance):
        self[self.reference_factory.from_model(instance)] = instance

    def add_all(self, instances):
        self.data.update({
            self.reference_factory.from_model(instance).to_key(): instance
            for instance in instances
        })


class RESTMeta(type):
    def __init__(cls, names, bases, dct):
        super().__init__(names, bases, dct)
        _classes_to_init.add(cls)


class StopDispatch(Exception):
    """
    Used to abort the current dispatch() invocation and immediately bail with any current errors.
    """
    pass


class Deferred:
    """
    Represents a deferred function call.

    Mainly used to construct result objects that depend on process_out on a particular instance before the changes
    to the actual instance have hit the database.
    """
    def __init__(self, fn):
        """
        :param fn: Callable that will be called when undeferring.
        """
        self.deferred = True
        self.value = None
        self.fn = fn

    def __call__(self):
        if self.deferred:
            self.deferred = False
            self.value = self.fn()
        return self.value

    def refresh(self):
        self.value = self.fn()
        return self.value

    @classmethod
    def partial(cls, fn, *a, **kw):
        return cls(functools.partial(fn, *a, **kw))


_NOT_FOUND = object()


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

    :cvar defer: If True, the default implementation will defer process_out() calls on insertions and updates to allow
        for the contents of the database to be refreshed in a more optimal fashion first.

    :ivar db: Database session
    :ivar method: Bottle request method being used.
    :ivar errors: List of accumulated errors.  If this list is not empty, dispatch() will return an appropriate error
        and rollback the transaction rather than allowing any modifications.
    :ivar options: Dictionary of possible options.
    :ivar auth: Authentication session information
    """
    url_prefix = config.API_PREFIX + 'v2/'
    url_base = None
    url_instance = '<key:int>'

    model = None
    bulk_max = None
    manager = None
    create_manager = None
    name = None

    allow_fetch = True
    allow_delete = False
    allow_delete_all = False
    allow_create = False
    allow_update = False
    allow_replace = False
    allow_replace_all = False
    allow_patch_create = False
    allow_patch_delete = False
    treat_put_as_patch = True

    SchemaClass = None

    defer = True

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
            return None if ref is None else ref.to_dict()

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
            if ref is not None:
                item['ref'] = ref
                if 'key' not in item:
                    ref.to_dict(item)
                elif ref != cls.manager.from_dict(item):
                    raise err.JSONValidationError(
                        "A key cannot be specified in this context unless it matches the context's key."
                    )
            else:
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
            method = bottle.request.method
            if method == 'HEAD':
                method = 'GET'
            allowed_methods = cls.collection_methods() if key is None else cls.item_methods()
            if 'GET' in allowed_methods:
                allowed_methods.add('HEAD')
            if method not in allowed_methods:
                response.add_header('Allow', ", ".join(allowed_methods))
                raise err.RequestNotAllowedError()

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

            instance = cls(db, options, auth=auth, method=request.method, ref=ref, data=data, params=params)
            try:
                rv = instance()
            except StopDispatch:
                pass
            except err.APIError as ex:
                db.rollback()
                ex.modify_response(response)
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
        bottle.route(cls.url_base, method='ANY', callback=callback)
        bottle.route(cls.url_base + '/' + cls.url_instance, method='ANY', callback=callback)

        # Setup reference manager.
        if cls.manager is None and cls.create_manager is not None:
            cls.manager = cls.create_manager()

    def __init__(self, db, options, method, ref, data, params, auth=None):
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
        self.method = method
        self.ref = ref
        self.data = data
        self.params = params
        self.schema = self.get_schema()
        self.schema.session = self.db
        self.cache = InstanceCache(query_factory=self.query, reference_factory=self.manager)

    def get_schema(self):
        """
        Returns a new instance of the Schema class.
        """
        return self.SchemaClass()

    def __call__(self):
        """
        Handles the second phase of dispatching.
        :param method: Request method
        :param ref: Reference
        :param data: Processed payload data
        :param params: Route parameters.
        :return: JSON response
        """
        if self.method in ('GET', 'HEAD'):
            return self.get()
        if self.method == 'DELETE':
            return self.delete()
        if self.method == 'PUT':
            return self.put()
        return self.patch()

    def query(self, ref=None, from_refresh=False):
        """
        Builds an SQL Query, possibly limited to a single instance (or set of instances) of our object.

        :param ref: Primary key reference(s).
        :param from_refresh: True if this is originating from a refresh() operation, in which case certain filters
            should not be applied.
        :return: Query.
        """
        query = self.db.query(self.model)
        if is_list(ref):
            query = query.filter(self.manager.sql_in(ref))
        elif ref is not None:
            query = query.filter(ref.sql_equals())
        return query

    def get_query(self, ref=None, query=None):
        """
        Builds an modified SQL Query intended for use for GET requests only, which may include extraneous data that
        we're not always interested in.

        The default implementation applies "limit" and "offset" options to the query if requested by the client.

        :param ref: Primary key reference(s).
        :param query: Base query to modify.  If None, calls self.query()
        :return: Query.
        """
        if query is None:
            query = self.query(ref)

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

    def get(self):
        """
        Called for GET requests.
        """
        query = self.get_query(self.ref)
        if self.ref:
            try:
                result = query.one()
            except orm.exc.NoResultFound:
                raise err.NotFoundError(ref=self.ref)
            return {'data': self.process_out(result)}
        else:
            return {'data': [self.process_out(row) for row in query]}

    def delete(self):
        """
        Called for DELETE requests.
        """
        query = self.query(self.ref)
        if self.options.get('quiet'):
            count = query.delete()
            response.status = http.client.NO_CONTENT if count else http.client.NOT_FOUND
            self.db.commit()
            return None

        data = []
        for instance in query:
            data.append(self.delete_item(instance))
        if not data:
            raise err.NotFoundError()
        self.db.commit()
        if self.ref:
            return {'data': data[0]}
        else:
            return {'data': data}

    def put(self):
        """
        Called for PUT requests (those that aren't... patched... to PATCH.
        :return:
        """
        raise NotImplementedError("PUT is not implemented.")

    def preload(self, data=None, _is_refresh=False):
        """
        Bulk-updates the instance cache.
        :param data: Data dictionary to use.  If None, uses self.data
        :return:
        """
        if data is None:
            data = self.data

        refs = tuple(item['ref'] for item in listify(self.data) if item['ref'] is not None)
        if not refs:
            return

        self.cache.add_all(self.query(ref=refs, from_refresh=_is_refresh))
        # result = query.merge_all(query)
        # self.cache.add_all(query.merge_all(query))

    refresh = functools.partialmethod(preload, _is_refresh=True)

    def patch(self):
        """
        Called for PATCH requests.  Also called for POST requests, which are converted to PATCH.
        :return:
        """
        rv = []
        must_exist = self.options.get('must-exist', True)
        deletes_must_exist = self.options.get('deletes-must-exist', must_exist)
        updates_must_exist = self.options.get('updates-must-exist', must_exist)

        self.preload()

        for index, item in enumerate(listify(self.data)):
            ref = item['ref']
            value = item['value']

            if ref:
                try:
                    instance = self.cache[ref]
                except KeyError:
                    if (deletes_must_exist and value is None) or (updates_must_exist and value is not None):
                        self.errors.append(err.NotFoundError(ref=ref))
                    continue
            else:
                instance = self.model()

            try:
                if value is None:
                    result = self.delete_item(instance)
                else:
                    self.process_in(value, instance)
                    self.validate(instance)
                    if ref:
                        result = self.update_item(instance)
                    else:
                        result = self.insert_item(instance)
                if result is not None:
                    rv.append(result)
            except err.APIError as ex:
                if ex.ref is None:
                    if ref is None:
                        ex.ref = {'index': index}
                    else:
                        ex.ref = ref
                self.errors.append(ex)

        if self.errors:
            raise StopDispatch()
        if self.defer:
            self.refresh()
            rv = self.undefer(rv)
        self.db.commit()

        if not is_list(self.data):
            return rv[0]
        return rv

    def process_out(self, instance=None, ref=None, defer=False):
        """
        Formats data for JSON output.  Returns a dictionary or other serializable object.

        This works by passing an instance through self.schema.dump() to perform the actual formatting.

        :param instance: Instance to serialize.  May be None, in which case the serialization process is skipped and
            the 'value' key of the return value will be None/null.
        :param ref: Reference identifying the instance.  May be None, in which case it is detected from the passed
            instance.
        :param defer: If True, returns a Deferred object representing an invocation with this parameter False.
            If None, defaults to the value of self.defer

        It is an error if both instance and ref are None.
        """
        if ref is None and instance is None:
            raise ValueError('At least one of ref or instance must be non-None.')

        if defer is None:
            defer = self.defer
        if defer:
            return Deferred.partial(self.process_out, instance, ref, defer=False)
        if ref is None:
            ref = self.manager.from_model(instance)
        if instance is None:
            value = None
        else:
            value = self.schema.dump(instance).data
        return ref.to_dict({'value': value})

    def process_in(self, value, instance):
        """
        Parses incoming JSON data and applies it to an instance.

        :param value: Incoming JSON data.
        :param instance: Instance to apply values to.
        """
        result = self.schema.load(value, instance=instance)
        if result.errors:
            self.errors.append(err.ValidationError(ref=ref))

    def undefer(self, results):
        """
        Undefers any item in results that is deferred.  The list is modified in place.
        :param results: List of results.
        :return: List of results.
        """
        for index, item in filter(lambda x: isinstance(x[1], Deferred), enumerate(results)):
            results[index] = item()
        return results

    def validate_delete(self, instance):
        """
        Validates a deletion against a single (confirmed to be existing) instance.

        Returns True if valid, False if not valid.  If returning False, self.errors should also be modified.  May
        raise an APIError instead.
        """
        return True

    def validate(self, instance):
        """
        Validates an instance's current state, whether an UPDATE or INSERT.  Used as a convenience function since both
        of those validation procedures are usually identical.

        Returns True if valid, False if not valid.  If returning False, self.errors should also be modified.  May
        raise an APIError instead.
        """
        return True

    def validate_update(self, instance): return self.validate(instance)

    def validate_insert(self, instance): return self.validate(instance)

    def delete_item(self, instance):
        if not self.validate_delete(instance):
            return None
        self.db.delete(instance)
        try:
            self.db.flush()
        except exc.IntegrityError:
            self.db.rollback()
            raise err.DatabaseIntegrityViolation(ref=self.manager.from_model(instance))
        return self.process_out(None, self.manager.from_model(instance), defer=False)

    def update_item(self, instance):
        if not self.validate_update(instance):
            return None
        self.db.add(instance)  # Probably already there anyways.
        self.db.flush()
        return self.process_out(instance, defer=self.defer)

    def insert_item(self, instance):
        if not self.validate_insert(instance):
            return None
        self.db.add(instance)  # Probably already there anyways.
        self.db.flush()
        return self.process_out(instance, defer=self.defer)


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

    def get_query(self, ref=None, query=None):
        query = super().get_query(ref, query)
        if ref is not None and not is_list(ref):
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
    def query(self, ref=None, from_refresh=False):
        query = super().query(ref, from_refresh)
        if from_refresh:
            return query

        field = self.model.date_inactive
        inactive = self.options.get('inactive')
        if inactive:
            if inactive == 'only':
                return query.filter(field.isnot(None))
            return query
        return query.filter(field.is_(None))

    def process_in(self, value, instance):
        super().process_in(value, instance)

        set_active = value.get('set-active')
        if set_active is None:
            return
        if set_active:
            instance.date_inactive = None
        elif instance.date_inactive is None:
            instance.date_inactive = datetime.datetime.now()
