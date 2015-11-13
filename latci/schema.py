"""
JSON model description/definition using Marshmallow and friends.

This builds heavily upon Marshmallow_SQLAlchemy but adds some of our own serialization protocol as well, including
replacing references with URLs, indirect references rather than duplicating data, and not always returning a collection.

A huge chunk of this relies on an options declaration mechanism that allow for a variety of behaviors to be configured.
Options are 'scoped' in such a way where they may or may not apply to nested serializers.

CONFIGURATION:

The following options can be set on SchemaState using the scoping mechanisms available in this file:

All defaulting to False:
can_link: When this is related to another object, can the linkage be changed?
can_merge: Can changes be merged into an instance of this object?
can_create: Can we create new instances of this object?
can_replace: Can we replace instances of this object?
can_upsert: Can we upsert instances of this object?
can_unlink: Can we unlink instances of this object?
can_delete: Can we delete instances of this object?
can_modify: if False, all above permissions are treated as False regardless of value.

All defaulting to False:
can_patch_collection: Can we patch a collection of this?
can_replace_collection: Can we replace a collection of this?

All defaulting to False for the /* scope, otherwise True.  All require the corresponding non-collection version to be
True as well to take effect:
can_collection_link
can_collection_merge
can_collection_create
can_collection_replace
can_collection_upsert
can_collection_unlink
can_collection_delete
can_collection_modify
"""
import marshmallow_sqlalchemy.schema
import marshmallow_sqlalchemy.convert
import marshmallow
import marshmallow.fields
import marshmallow.utils
import latci.config
import operator
from sqlalchemy import inspect, sql
import collections
import collections.abc
import functools

__all__ = ['Related', 'URLTranslator', 'SchemaOptions', 'SchemaMeta', 'Schema', 'CachedInstance',
           'SchemaState', 'ScopedOption', 'Scope', 'SortedDict']
_MISSING = object()
_default = object()


class Related(marshmallow.fields.Nested):
    """
    A field relating to another SQLAlchemy instance.

    Utilizes a lot of the logic from marshmallow.fields.Nested, but wraps it around our own definitions.

    :ivar prop: SQLAlchemy property that we describe
    :ivar remote_mapper: The mapper representing the remote end of the property.
    :ivar remap: Dictionary of attributes that are remapped.
    :ivar remap_strict: Whether any remapping should be strict or not.
    :ivar nested: The nested schema.  (Automatically determined if None)
    """

    # We don't want Marshmallow to lookup the field value for us, because that will inconveniently cause SA to do
    # lazy-loading that we don't want.
    _CHECK_ATTRIBUTE = False

    def __init__(self, prop, **kwargs):
        """
        Creates a new Related field

        :param prop: SQLAlchemy RelationshipProperty identifying the relationship.
        :param kwargs: Passed to superclass

        The 'info' dictionary of the RelationshipProperty can be used to override some of the default behaviors, as
        described below.

        If the relationship is a one-to-many or many-to-many relationship, this will automatically serialize to a list
        of objects.  Otherwise, this serializes to a single object.  info['uselist'] overrides this behavior if it is
        defined and not None.

        Relationships have a unique URL, which is exposed if the relationship is a list.  This URL defaults to
        parent_object_url/property_name.  If info['url'] is defined, it overrides the URL entirely (and is called
        to determine it if it is callable).  Otherwise, if info['suffix'] is defined, it overrides the URL suffix
        (changing it from property_name).  info['url'] is rarely useful.

        To determine URLs for the related object(s) without loading them, Related generates a dictionary of attribute
        remappings.  If the target instance has a 'parent_id' field that refers to a parent's 'id' field, for instance,
        the dictionary will contain {'id': 'parent_id'}.  info['remap'] overrides the remap dictionary and stops it
        from being automatically computed.

        URLTranslator by default requires all primary key attributes to be named in the remap dictionary, otherwise
        it generates this behavior.  To override that option, set info['remap_strict'] to True.

        Note that URL generation for related object(s) is only done when this does not represent a list, since in order
        for a list to be loaded all of the related objects are already present anyways.
        """
        self.prop = prop
        self.remote_mapper = self.prop.mapper

        info = prop.info
        many = info.get('uselist')
        if many is None:
            many = prop.direction.name.endswith('MANY')
        if many:
            self.remap = None
            self.remap_strict = None
        else:
            remap = info.get('remap')
            if remap is None:
                remap = {
                    remote.name: local.name
                    for local, remote in prop.local_remote_pairs
                }
            self.remap = remap
            self.remap_strict = info.get('strict', True)

        super().__init__(None, many=many, **kwargs)
        self._nested = None

    @property
    def nested(self):
        """
        marshmallow.fields.Nested isn't really designed to be very subclassable, and it does some less than desirable
        things.

        We define a 'nested' property and do some associated trickery to allow it to be late-initialized without having
        to copy+modify half of the code that Nested uses.
        """
        if self._nested is None:
            self._nested = self.remote_mapper.class_.Schema
        return self._nested

    @nested.setter
    def nested(self, value):
        self._nested = value

    def _serialize(self, nested_obj, attr, obj):
        """
        Create our own structure and potentially incorporate the output of our superclass into it.
        :param nested_obj: Not used.  We compute our own to pass to the superclass.
        :param attr: Attribute name we're examining.
        :param obj: Object with the attribute (an instance from SQLAlchemy)
        :return: Serialized data.

        Bugs: Probably doesn't work with NULL values, but this schema has no nullable foreign keys.
        """
        schema = self.schema
        schema.adopt_parent(self.parent, attr)
        loaded = attr not in inspect(obj).unloaded
        nested_obj = getattr(obj, attr) if loaded else None
        if self.many:
            rv = {
                '_type': schema.typename,
                '_link': self.relation_url(attr, obj),
                '_items': None
            }
            if loaded:
                rv['_items'] = super()._serialize(nested_obj, attr, obj)
            return rv
        if nested_obj is None:
            return {
                '_type': schema.typename,
                '_link': None if loaded else schema.translate.url_for(obj, self.remap, strict=self.remap_strict)
            }
        else:
            return super()._serialize(nested_obj, attr, obj)

    def serialize(self, attr, obj, accessor=None):
        """
        Insures that the object we're examining is not a CachedInstance, since we shouldn't be even returning a value
        in that event.

        :param attr: Attribute to look for
        :param obj: Object containing attribute
        :param accessor: Function to retrieve attribute.
        :return: Serialized data.

        Bugs: Probably doesn't work with NULL values, but this schema has no nullable foreign keys.
        """
        if isinstance(obj, CachedInstance):
            if callable(self.default):
                return self.default()
            else:
                return self.default
        return super().serialize(attr, obj, accessor)

    def _deserialize(self, value, attr, data):
        """
        Deserialize input.
        :param value:
        :param attr:
        :param data:
        :return:

        This is going to be a bit tricky to implement.  There's a few possibilities here:

        For *-to-one relationships:
        There's a chance that the client may want to simply change what instance of an object we point to.  In that
        case, we should see an appropriate _link attribute and retrieve that instance (to verify its existence) or
        throw a validation error.

        The client might also want to alter the nested object -- or potentially even create a brand new one.  We need
        a way to differentiate these two events -- likely by something special with the _link attribute.  Perhaps
        _link = None for the 'create' case, but then a buggy client might inadvertently start creating items when it
        doesn't mean to.

        Lastly, the client might want to un-associate the related instance -- or it might want to delete the related
        instance.

        For *-to-many relationships:
        We have all of the above possibilities, but they apply to every item on the list.

        Additionally, there's the question of what the list itself is:
        * Is it a list of changes to apply, or
        * Does it completely replace the original list?

        Proposed solution:

        Individual item within the list, or the individual item if this isn't a list, have an _action attribute.

        It can have the following values:
            'link': Change linkage only.  Does not modify any attributes of the linked object.  This is the default
                if no actual fields are present.
                _link must be specified and non-NULL.
            'merge': In addition to changing the linkage, apply modifications to the linked object.  This is the
                default if fields are present in the response.
                _link must be specified and non-NULL.
            'create': Create a new instance, apply the modifications to it, and link it.
                _link must be NULL if specified, unless writable primary keys are allowed.
            'replace': Create a new instance, apply the modifications to it, and link it.  If an object already
                existed at the specified _link, it is removed first.
                _link must be specified and non-NULL.
            'upsert': Create a new instance, apply the modifications to it, and link it.  If an object already existed,
                merge instead.
                _link must be specified and non-NULL.
            'unlink': Unlink associated item (set reference to NULL).
                _link must be either be NULL or exactly match the linked instance if specified.
                Within a list, _link cannot be NULL.
            'delete': Delete the associated item.
                _link must be either be NULL or exactly match the linked instance if specified.
                Within a list, _link cannot be NULL.

            Certain actions can be followed by a question mark (e.g. 'create?') to modify their behavior:
            'create?': Does not fail if an object already exists at the same URL, does nothing instead.
            'unlink?': Does not fail if the _link did not match, does nothing instead.
            'delete?': Does not fail if the _link did not match, does nothing instead.

        The list itself may specify an _action as well:
            'patch': Apply items in this list as patches against the actual list.
            'replace': Replace the entire collection with the new list.  Items in the new list should not specify
        """
        raise ValueError("TODO: Find a way to implement deserialize in a sane manner.")
        pass

    def relation_url(self, attr, obj):
        """
        Determines the URL for this collection.
        :param attr: Attribute name.
        :param obj: Containing object.
        :return:
        """
        info = self.prop.info
        url = info.get('url')
        if url is not None:
            return url(obj) if callable(url) else url
        suffix = info.get('suffix')
        if suffix is None:
            suffix = attr
        return self.parent.translate.url_for(obj) + "/" + suffix


class URLTranslator:
    """
    Handles translating between URLs and objects.

    :cvar date_format: Format for dates (used by date.strftime() and datetime.datetime.strptime()).  Under this
        implementation, must not contain any hyphens as they're used to split URL components.
    :cvar time_format: Format for times, as above.
    :cvar datetime_format: Format for datetimes, as above.

    :ivar mapper: Mapper that we reference.
    :ivar typename: Typename, used by Schema for the _type attribute.
    :ivar to_fragment: Function that converts a dictionary to a URL fragment.
    :ivar from_fragment: Function that converts a URL fragment to a dictionary.
    :ivar prefix: URL prefix, which also identifies the entire collection rather than a single item.
    :ivar fields: Listing of all fields used by {to,from}_url.

    Most uses of URLTranslator should not call the to_url() and from_url() directions directly.  Instead, use
    url_for, instance_from, or pk_from.
    """
    date_format = "%Y%m%d"
    time_format = "%H%M%S.%f"
    datetime_format = date_format + time_format

    def __init__(self, mapper, to_key, from_key, fields, prefix=None, typename=None):
        """
        Creates a new URLTranslator.

        :param mapper: SQLAlchemy mapper for this type of object.
        :param to_key: Function that receives {field: value} pairs and returns the key component for the URL.
        :param from_key: Function that receives a key component and returns {field: value} pairs.
        :param fields: List of attributes we consider on target objects.  Used for remapping.
        :param prefix: Base URL to use.  Automatically configured if None
        :param typename: Typename.  Automatically configured if None.
        """
        if prefix is None:
            prefix = latci.config.API_PREFIX + 'v2/' + mapper.__name__.lower()
        if typename is None:
            typename = mapper.__name__.lower()

        self.mapper = mapper
        self.typename = typename
        self.to_key = to_key
        self.from_key = from_key
        self.prefix = prefix
        self.fields = fields

    def _setprefix(self, value):
        if value[-1] == '/':
            value = value[:-1]
        self._prefix = value
        self._prefixslash = value + '/'

    prefix = property(
        fget=lambda self: self._prefix, fset=_setprefix, doc="The URL prefix to use, with no trailing slash."
    )
    prefixslash = property(
        fget=lambda self: self._prefixslash, fset=_setprefix, doc="The URL prefix to use. Includes a trailing slash"
    )

    @classmethod
    def from_mapper(cls, mapper, **kwargs):
        """
        Creates a new URLMapper using primary key columns from the mapper.

        :param mapper: SQLAlchemy mapper to inspect.
        :param **kwargs: Additional kwargs sent to __init__.
            Should not include to_key, from_url, or fields.
        """
        from datetime import date, time, datetime
        strptime = datetime.strptime

        pk = inspect(mapper).primary_key
        if not len(pk):
            raise ValueError("Mapper has no primary key.")

        fields = [col.name for col in pk]

        mapping = []
        for col in pk:
            type_ = col.type.python_type
            if issubclass(type_, int):
                mapping.append((col.name, str, int))
            elif issubclass(type_, date):
                mapping.append((
                    col.name,
                    lambda x: x.strftime(cls.date_format),
                    lambda x: strptime(x, cls.date_format).date()
                ))
            elif issubclass(type_, datetime):
                mapping.append((
                    col.name,
                    lambda x: x.strftime(cls.datetime_format),
                    lambda x: strptime(x, cls.datetime_format)
                ))
            elif issubclass(type_, time):
                mapping.append((
                    col.name,
                    lambda x: x.strftime(cls.time_format),
                    lambda x: strptime(x, cls.time_format).time()
                ))
            elif issubclass(type_, str):
                if len(pk) == 1:
                    return cls(
                        mapper,
                        to_url=lambda x, _n=col.name: x[_n],
                        from_url=lambda x, _n=col.name: {n: x},
                        attrs=fields, prefix=prefix
                    )
                else:
                    raise ValueError("Composite primary keys containing str are not implemented.")
            else:
                raise ValueError("Type {!r} is not supported in primary key columns.", type_)

        def to_key(x):
            return "-".join(f_to(x[field]) for field, f_to, f_from in mapping)

        def from_key(x):
            chunks = x.split("-")
            if len(chunks) != len(mapping):
                raise ValueError("Invalid URL fragment.")
            return {
                field: f_from(chunk)
                for chunk, (field, f_to, f_from) in zip(chunks, mapping)
            }

        return cls(mapper, to_key=to_key, from_key=from_key, fields=fields, **kwargs)

    def url_for(self, instance, remap=None, strict=True):
        """
        Creates a URL from a SQLAlchemy instance.

        :param instance: Instance to create URL from
        :param remap: If set, consists of a dictionary of attribute mappings. {from: to}.
            When to_key() would call for the 'to' attribute, 'from' is provided instead.
        :param strict: If set and remap is non-None, fail if not all attributes are mapped.
        :return: Full URL.
        """
        if remap is None:
            return self.prefixslash + self.to_key(
                dict((attr, getattr(instance, attr)) for attr in self.fields)
            )

        if strict:
            missing = set(self.fields) - set(remap)
            if missing:
                raise ValueError(
                    "Not all attributes are properly remapped.  Missing: " + ", ".join(
                        "'" + attr + "'" for attr in sorted(missing)
                    )
                )

        return self.prefixslash + self.to_key(
            dict((attr, getattr(instance, remap.get(attr, attr))) for attr in self.fields)
        )

    def key_from_url(self, url):
        """
        Returns just the key component from a full URL.

        :param url: URL to parse
        :return: key
        :raises: ValueError if the URL does not begin with self.prefixslash
        """
        if not url.startswith(self.prefixslash):
            raise ValueError(
                "URL {!r} does not belong to this translator (prefix={!r})"
                .format(url, self.prefix)
            )
        return url[len(self.prefixslash):]

    def from_url(self, url):
        """
        Analog to from_key, but reading a full URL.  Shortcut for from_key(key_from_url(url))
        :param url: URL to parse
        :return: Primary key dictionary.
        """
        return self.from_key(self.key_from_url(url))

    def instance_from(self, url=None, key=None):
        """
        Returns an instance from a full URL or a key component.

        :param url: Full URL
        :param key: Key component.
        :return: SQLAlchemy instance

        It is an error to specify both key and url.
        """
        if (url is None) is not (key is None):
            raise ValueError("Exactly one of 'url' or 'key' must be specified and non-None.")
        if url is not None:
            key = self.key_from_url(url)
        d = self.from_key(key)
        instance = self.mapper()
        for attr, value in d.items():
            setattr(instance, attr, value)
        return instance

    def pk_from(self, url=None, key=None):
        """
        Returns a primary key tuple from a full URL or a key component.

        :param url: Full URL
        :param key: Key component.
        :return: Primary key tuple

        It is an error to specify both key and url.
        """
        if (url is None) is not (key is None):
            raise ValueError("Exactly one of 'url' or 'key' must be specified and non-None.")
        if url is not None:
            key = self.key_from_url(url)
        d = self.from_key(key)
        pk = inspect(self.mapper).primary_key
        rv = []
        for col in pk:
            rv.append(d[col.name])
        if len(rv) == 1:
            return rv[0]
        return tuple(rv)

    def expression_from(self, url=None, key=None):
        """
        Return an SQLAlchemy expression (e.g. 'id=2') from a full URL or a key component.
        :param url: Full URL
        :param key: Key component.
        :return: Expression

        It is an error to specify both key and url.
        """
        if (url is None) is not (key is None):
            raise ValueError("Exactly one of 'url' or 'key' must be specified and non-None.")
        if url is not None:
            key = self.key_from_url(url)
        d = self.from_key(key)
        pk = inspect(self.mapper).primary_key
        return sql.and_(col == d[col.name] for col in pk)

class CachedInstance:
    """
    When we're dumping objects and the object we're dumping is already part of this schema's catalog, replace it with
    a CachedInstance instead.  CachedInstance redirects only certain fields to the underlying object (usually just the
    ones that are used to produce its URL), and pretends all other fields don't exist.
    """
    def __init__(self, obj, fields):
        """
        Creates a new CachedInstance

        :param obj: Object we refer to.
        :param fields: Fields that are allowed to exist.
        """
        self._obj = obj
        self._fields = set(fields)

    def __getattr__(self, attr):
        if attr in self._fields:
            return getattr(self._obj, attr)
        raise AttributeError(attr)


class SchemaOptions(marshmallow_sqlalchemy.schema.ModelSchema.OPTIONS_CLASS):
    """
    Custom options for our Schema class.  All marshmallow and marshmallow_sqlalchemy options are supported, along with
    the following:

    writable_pk: If True, primary key columns are allowed to be serialized/deserialized.
    translate: Defines a custom URLTranslator for this schema.  One is automatically created from the Mapper otherwise.
    """
    def __init__(self, meta):
        super().__init__(meta)
        if self.model is None:
            return

        self.pk = self.model.__table__.primary_key.columns
        self.writable_pk = getattr(meta, 'writable_pk', False)
        self.include_pk = getattr(meta, 'include_pk', False)
        if not self.writable_pk:
            if not self.include_pk:
                self.exclude += tuple(col.name for col in self.pk)
            else:
                self.dump_only += tuple(col.name for col in self.pk)
        self.dump_only += ('_link', '_type')

        self.translate = getattr(meta, 'translate', None)
        if self.translate is None:
            self.translate = URLTranslator.from_mapper(self.model)


class SchemaMeta(marshmallow_sqlalchemy.schema.ModelSchemaMeta):
    """
    Custom MetaClass for our Schema class.  Mostly, this overrides the superclass to create our own Related properties
    rather than using marshmallow_sqlalchemy's implementation.
    """
    @classmethod
    def get_fields(mcs, converter, opts):
        fields = super().get_fields(converter, opts)
        if opts.model is not None:
            for prop in inspect(opts.model).iterate_properties:
                if prop.key not in fields:
                    continue
                if hasattr(prop, 'direction'):
                    fields[prop.key] = Related(prop)
            fields['_link'] = marshmallow.fields.Function(lambda obj: opts.translate.url_for(obj))
            fields['_type'] = marshmallow.fields.Constant(opts.translate.typename)
        return fields


class SortedDict(collections.UserDict):
    """
    Dictionary of sorted keys.

    Unlike OrderedDict, where keys are sorted by insertion order, SortedDicts create and sorts a list of all keys when
    needed.
    """
    def __init__(self, key=None, reverse=False, iterable=None):
        """
        Creates a new SortedDict.

        :param key: As per the corresponding argument of sorted()
        :param reverse: As per the corresponding argument of sorted()
        """
        self._keys = None
        self._sortfn = functools.partial(sorted, key=key, reverse=reverse)
        super().__init__(iterable)

    def sort(self):
        """
        Stable sort of dictionary keys *IN PLACE*
        """
        self._keys = list(self._sortfn(self.data.keys()))

    def __setitem__(self, key, item):
        if key not in self:
            self._keys = None
        return super().__setitem__(key, item)

    def __delitem__(self, key):
        if key in self:
            self._keys = None
        return super().__delitem__(key)

    def __iter__(self):
        if self._keys is None:
            self.sort()
        try:
            for k in self.data:
                if self._keys is None:
                    raise RuntimeError("Dictionary keys modified during iteration.")
                yield k
        except KeyError:
            raise RuntimeError("Dictionary keys modified during iteration.")


class Scope(tuple):
    """
    CONFIGURATION SCOPES:
    Since returned results may end up being heavily nested, configuration directives all have a scope that they apply to:

    '*' applies to all schemas.
    'typename' applies to all schemas that are looking at a particular typename.
    'typename/parent' applies to schema instances created by typename's 'parent' Related field.
    'typename/*' applies to all schema instances created by any Related field on typename.

    Scopes can be nested, e.g. 'typename/parent/grandparent' refers to Typename's parent's grandparent schema.

    '*' wildcards must be the final component of the scope.

    Scopes beginning with '/' are anchored to the top-level schema.  '/*' refers to all top-level schemas (regardless of
    type)

    PRECEDENCE:
    When conflicting options are defined at multiple scopes, the following algorithm chooses the winner:

    The 'longest' scope is chosen first, determined by counting the number of slashes.  'a/b' is thus longer than 'foobar'

    If there's a tie for longest scope, a rooted scope (leading /) wins

    If there's still a tie, a non-wildcard scope wins over a non-wildcard scope.
    """
    def __new__(cls, s):
        rv = super().__new__(cls, [s[0] == '/'] + list(filter(None, reversed(s.split("/")))))
        setattr(rv, '_key', 3*len(rv) + (1 if rv[0] else 0) + (0 if rv[1] == '*' else 1))
        return rv

    def __str__(self):
        return ('/' if self[0] else '') + "/".join(self[:0:-1])  # Slice syntax: All but the first item of the iter, reversed

    def __repr__(self):
        return "{}({!r})".format(type(self).__name__, str(self))

    def applies_to(self, schema):
        """
        Returns TRUE if this scope applies to the specified schema.

        :param schema: Schema
        :return: True or False
        """
        last = len(self) - 1
        for ix in range(1, len(self)):
            if ix == last:
                if self[0] and schema.adopted_parent is not None:
                    return False  # We're rooted, and the schema wasn't.
                name = schema.typename
            else:
                if schema.adopted_parent is None:  # We have no parent, but there's at least one more level to go.
                    return False
                name = schema.adopted_relation
            if name is None:  # We have no name
                return False
            if not ((ix == 1 and self[ix] == '*') or self[ix] == name):
                return False
            if ix != last:
                schema = schema.adopted_parent
        return True

    def __eq__(self, other):
        return type(self) == type(other) and super().__eq__(other)

    def __hash__(self):
        return super().__hash__() ^ 41207233  # a


class ScopedOption(SortedDict):
    _keyfunc = operator.attrgetter('_key')

    def __init__(self, *args, **kwargs):
        iterable = dict(args, **kwargs)
        super().__init__(key=self._keyfunc, reverse=False, iterable=iterable)

    def matching_scope(self, schema):
        for scope in self.keys():
            if scope.applies_to(schema):
                return scope
        return None

    def value_for(self, schema, default=_MISSING):
        scope = self.matching_scope(schema)
        if scope is None:
            if default is _MISSING:
                raise KeyError("No value was found that matches this schema's scope.")
            return default
        return self[scope]


class SchemaState:
    """
    Defines state that is common to a given instance of a Schema and all of its children.

    :ivar catalog: Catalog of previously-cached instances.  Dict of { RealInstance: CachedInstance }
    """
    instance_permissions = {'link', 'merge', 'create', 'replace', 'upsert', 'unlink', 'delete', 'modify'}
    collection_permissions = {'patch', 'replace'}

    def __init__(self, catalog=None):
        """
        Creates a new SchemaState

        :param catalog: dict defining the catalog contents.
        """
        if catalog is None:
            catalog = {}
        self.catalog = catalog
        self.options = {}
        self._scopes = {}
        self.setscope('*', {"can_{}".format(permission): False for permission in self.instance_permissions})
        self.setscope('*', {"can_collection_{}".format(permission): True for permission in self.instance_permissions})
        self.setscope('/*', {"can_collection_{}".format(permission): False for permission in self.instance_permissions})
        self.setscope('*', {"can_{}".format(permission): False for permission in self.collection_permissions})

    def cache(self, obj, fields):
        """
        Add obj to the cache.

        Returns obj if the obj was not already cached, otherwise returns a CachedInstance defining it.
        """
        if obj in self.catalog:
            return self.catalog[obj]
        self.catalog[obj] = CachedInstance(obj, fields)
        return obj

    def merge(self, other):
        """
        Incorporates state from another SchemaState into this SchemaState.  Returns self.

        :param other: Schema to merge
        :return: self
        """
        self.catalog.update(other.catalog)
        return self

    def get(self, option, schema, default=_MISSING):
        """
        Returns an option value that is within the schema's scope.
        :param option: Option name
        :param schema: Schema to test
        :param default: Default value if option not defined.
        :return: Defined option
        """
        opt = self.options.get(option)
        if opt is None:
            if default is _MISSING:
                raise KeyError("Option '{}' is not defined in any scopes.".format(option))
            return default
        return opt.value_for(schema)

    def set(self, scope, option, value):
        """
        Sets a single option in a single scope.
        :param scope: Scope
        :param option: Option name
        :param value: Value
        :return: None
        """
        scope = self._scope(scope)
        if option not in self.options:
            self.options[option] = ScopedOption()
        self.options[option][scope] = value

    def setscope(self, scope, options):
        """
        Sets a dictionary of option in a single scope.  Updates any existing options present.
        :param scope: Scope
        :param options: Dictionary of {option: value}
        :return: None
        """
        scope = self._scope(scope)
        for option, value in options.items():
            if option not in self.options:
                self.options[option] = ScopedOption()
            self.options[option][scope] = value

    def _scope(self, s):
        if isinstance(s, Scope):
            return s
        if s not in self._scopes:
            self._scopes[s] = Scope(s)
        return self._scopes[s]


# noinspection PyAbstractClass
class Schema(marshmallow_sqlalchemy.schema.ModelSchema, metaclass=SchemaMeta):
    """
    Our custom Schema base class.

    :cvar OPTIONS_CLASS: Defines what class defines SchemaOptions.
    :ivar adopted_parent: Refers to the parent schema.  We don't use 'parent' since marshmallow presumably uses it
        for other things.
    :ivar adopted_relation: Name for the relationship that our parent uses to connect to us.
    :ivar state: A SchemaState representing shared global state.
    """
    OPTIONS_CLASS = SchemaOptions
    adopted_parent = None
    adopted_relation = None

    @property
    def translate(self):
        return self.opts.translate

    @property
    def typename(self):
        return self.translate.typename

    def adopt_parent(self, parent, relation):
        """
        Set our parent schema to parent.

        Since implementation details mean this method is called multiple times, this is a no-op if we already have
        a parent defined and it's the same parent.

        :param parent: Parent schema to adopt
        :param relation: Relation that connected our parent to us
        :raises: ValueError if a parent is already defined and doesn't match the specified parent.
        """
        if self.adopted_parent is None:
            self.state = parent.state.merge(self.state)
            self.adopted_relation = relation
        elif self.adopted_parent is not parent:
            raise ValueError("Schema already has a parent.")
        elif self.adopted_relation is not relation:
            raise ValueError("Schema already adopted via a different relation.")
        return self.adopted_parent

    def cache(self, obj):
        """
        Forwards to self.state.cache
        """
        return self.state.cache(obj, self.translate.fields)

    def __init__(self, *args, **kwargs):
        """
        Creates a new instance of this Schema.

        :param state: If specified, determines the SchemaState we have.
        :param catalog: If specified, determines the initial catalog.  Ignored if 'state' is present.
        """
        super().__init__(*args, **kwargs)
        self.state = kwargs.pop('state', None)
        if self.state is None:
            self.state = SchemaState(catalog=kwargs.pop('catalog', None))

    def dump(self, obj, many=None, *args, **kwargs):
        """
        Wraps around the superclass's serialize() method to ensure obj is replaced with CachedInstances when relevant.
        """
        many = self.many if many is None else bool(many)
        if not many:
            return super().dump(self.cache(obj), many, *args, **kwargs)
        return super().dump([self.cache(o) for o in obj], many, *args, **kwargs)

    def get_instance(self, data):
        """Retrieve an existing record by link attribute."""
        url = data.get('_link')
        if url is None:
            return None
        return self.session.query(self.opts.model).filter(self.translate.expression_from(url=url)).first()

    def load(self, data, session=None, instance=None, *args, **kwargs):
        return super().load(data, session, instance, *args, **kwargs)

    def get(self, option, default=_MISSING):
        return self.state.get(option, self, default)
