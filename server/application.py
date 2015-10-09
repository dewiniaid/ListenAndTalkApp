import bottle
from bottle import HTTPError
from bottle.ext import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, Sequence, String
from sqlalchemy.ext.declarative import declarative_base

from latci import config

# Set up database connectivity
engine = create_engine(config.DATABASE_PATH, echo=True)

# Set up WSGI application
app = bottle.Bottle()
app.install(
    sqlalchemy.Plugin(
        engine, # SQLAlchemy engine created with create_engine function.
        Base.metadata, # SQLAlchemy metadata, required only if create=True.
        keyword='db', # Keyword used to inject session database in a route (default 'db').
        create=False, # If it is true, execute `metadata.create_all(engine)` when plugin is applied (default False).
        commit=False, # If it is true, plugin commit changes after route is executed (default True).
        use_kwargs=False # If it is true and keyword is not defined, plugin uses **kwargs argument to inject session database (default False).
    )
)










