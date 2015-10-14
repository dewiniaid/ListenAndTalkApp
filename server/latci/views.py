from bottle import route
import bottle
from latci.database import models
from sqlalchemy import sql, orm


class RouterBase():
    """
    Base class for routers

    :cvar base_url: Base URL for generating bottle routes.  e.g. /student/
    :cvar id_fragment: URL suffix for interacting with individual items (as opposed to collections).  e.g. '<int:id>'
    :cvar model: SQLAlchemy model that this route primarily corresponds to.
    :cvar sql_map: Map of arguments occuring in the URL and the database columns they correspond to.
        Used for automatic WHERE clause generation.
    :cvar collection_actions: The string "CRUD", with optional missing letters to revoke permissions to the
        specified action.
        (C)reate: Allow creation of new objects in this collection  (HTTP POST)
        (R)ead: Allow retrieval of the entirety of this collection  (HTTP GET)
        (U)pdate: Allow the entire collection to be replaced with a different one.
        (D)elete: Allow the entire collection to be deleted.
        Default: CR
    :cvar instance_actions: The string "CRUD", with optional missing letters to revoke permissions to the
        specified action.  (See below)
        (C)reate: Allow creation of a new object with specific ID
        (R)ead: Allow retrieval of a single object
        (U)pdate: Allow updates on a single object
        (D)elete: Allow deletions on a single object.
        Default: CRUD
    """
    base_url = None
    id_fragment = None
    model = None
    sql_map = None
    db = None

    collection_actions = 'CR'
    instance_actions = 'CRUD'

    collection_route_name = None
    instance_route_name = None

    _methodmap = {
        'POST': 'C',
        'GET': 'R',
        'PUT': 'U',
        'DELETE': 'D'
    }

    @classmethod
    def create_routes(cls):
        if cls.base_url is not None:
            return

        cls.collection_route_name = cls.base_url + "/ALL"
        cls.instance_route_name = cls.base_url + "/ONE"

        bottle.route(cls.base_url, method=cls._methodmap.keys(), name=cls.collection_route_name)
        bottle.route(cls.base_url + cls.id_fragment, method=cls._methodmap.keys(), name=cls.instance_route_name)

    def is_collection(self):
        return bottle.request.route.name == self.collection_route_name

    def __init__(self, db, **kwargs):
        self.db = db

        # See if this action is permitted.
        actions = self.collection_actions if self.is_collection() else self.instance_actions
        if self._methodmap[bottle.request.method] not in actions:
            bottle.abort(405)  # Method Not Allowed

        # PUT and POST are going to require some sort of JSON data, so look for it
        if bottle.request.method in ('PUT', 'POST') and bottle.request.json is None:
            bottle.abort(400, 'JSON Body Expected')

    def sql_filter(self, d):
        """
        Returns an SQL Expression that can be used to filter a query based on
        :param d: Dictionary of arguments.  Keys must exist in self.sql_map and will be translated, values are
            interpreted as is
        :return: An expression suitable for passing to query.filter()
        """
        return sql.and_(*self.kw_map[key] == value for key, value in d.items())

    def sql_base_query(self, d):
        """
        Returns a basic SQL query for interacting with this type of object.
        :param d: Arguments passed from the view.  Not used in this implementation, but may be useful for subclasses.
        :return: A query
        """
        return db.query(self.model)

    def sql_query(self, d):
        """
        Returns a SQL query for interacting with this type of object, with filters applied.

        Unless overridden, this is shorthand for object.sql_query(d).filter(object.sql_filter(d))
        :param d: Arguments passed from the view.  Used primarily by sql_filter to generate a WHERE clause.
        :return: A query
        """
        return self.sql_base_query(d).filter(self.sql_filter(d))

    def read_json(self, json, obj):
        """
        Reads JSON data into a single instance of a database object.
        :return:
        """


class StudentRouter():
    base_url = '/students/'  # Base URL fragment
    id_fragment = '<int:id>'  # Parameters to determine primary key/unique identifier
    model = models.Student  # Database model

    sql_map = {  # Map URL parameters to database columns for automatic query generation
        'id': models.Student.id
    }


    def __init__(self, db, **kwargs):
        self.db = db



        def query(self, **kwargs):
        """
        Returns the basic SQL query to retrieve instances of this object.

        :param kwargs: Keyword arguments that may exist as part of the request.
        """
        return self.db.query(self.model)

    def get(self, id):
        """
        Returns a single instance of this object
        """
        return self.query().filter(self.model.id == id)

