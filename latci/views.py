from latci.api import rest
from latci.database import models
import latci.schema
from latci.api.references import ScalarReferenceManager
from sqlalchemy import sql, orm
import latci.config
import bottle
import functools

class RouteHandler:
    # Configure base SchemaState -- what permissions are allowed where, etc.
    base_state = latci.schema.SchemaState()
    base_state.setscope('/student', {
        'can_merge': True,
        'can_create': True,
        'can_delete': False,
        'can_modify': True,
    })

    def __init__(self, model, factory=None, create_route=None):
        """
        Creates a new RouteHandler and adds bottle routes
        :param factory: Factory that produces Schemas
        :param model: SQLAlchemy model.  Used to autodetect factory.
        :param create_route: Function called to add routes, defaults to bottle.route.
        """
        if factory is None:
            factory = model.Schema
        self.model = model
        self.factory = factory
        self.related_fields = factory.related_fields()
        if create_route is None:
            create_route = bottle.route

        url_many = self.factory.opts.translate.prefix
        url_one = url_many + "/<key>"
        create_route(url_many, 'ANY', self)
        create_route(url_one, 'ANY', self)

        for attr, field in self.related_fields.items():
            create_route(field.url_pattern(attr, prefix=url_one), 'ANY', functools.partial(self, attr=attr))

    def __call__(self, db, key=None, **kwargs):
        """
        Handles incoming HTTP requests to this schema's routes.

        :param db: SQLALchemy session
        :param key: Key uniquely identifying a single item, or None in the case of the entire collection.
        :param attr: If set, incoming payload and output results refer to just this attribute of the item rather than
            the entire item.
        :return:

        BUGS:
        **kwargs really ought to just be attr=None, but there's a bug in bottle-sqlalchemy that causes it to raise
        when combined with functools.partial and that signature.
        """
        attr = kwargs.get('attr', None)
        field = None
        if attr is not None:
            field = self.related_fields.get(attr)
            if key is None or field is None:
                # Theoretically not possible because of how urls are bound in __init__, but check anyways.
                raise bottle.HTTPError(400)


        state = self.base_state.clone()
        schema = self.factory(state=state, session=db)
        url = bottle.request.path
        method = bottle.request.method
        if method == 'HEAD':
            method = 'GET'  # Fakery

        payload = bottle.request.json  # May be None.

        # For now, let's just handle read-only
        query = db.query(self.model).options(orm.lazyload_all('*'))
        if key is None:
            obj = query
            many = True
        else:
            if field is not None:
                query = query.options(orm.subqueryload(field.prop.class_attribute))
            obj = query.filter(schema.translate.expression_from(key=key)).first()
            many = False
            if obj is None:
                raise bottle.HTTPError(404)

        output, errors = schema.dump(obj, many)
        if attr is not None:
            output = output[attr]

        return {'data': output}

RouteHandler(models.Staff)
RouteHandler(models.Activity)
RouteHandler(models.Student)
