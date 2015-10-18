import bottle
from bottle import route
from bottle import HTTPError
# from bottle.ext import sqlalchemy
import sqlalchemy
import bottle.ext.sqlalchemy
import sqlalchemy.event
import latci.database

from latci import config
import latci.json

# Set up WSGI application
bottle.install(
    bottle.ext.sqlalchemy.Plugin(
        latci.database.engine, # SQLAlchemy engine created with create_engine function.
        None, # SQLAlchemy metadata, required only if create=True.
        keyword='db', # Keyword used to inject session database in a route (default 'db').
        create=False, # If it is true, execute `metadata.create_all(engine)` when plugin is applied (default False).
        commit=False, # If it is true, plugin commit changes after route is executed (default True).
        use_kwargs=False # If it is true and keyword is not defined, plugin uses **kwargs argument to inject session database (default False).
    )
)
# Uninstall the JSON plugin Bottle installs by default, and add one configured the way we want.
app = bottle.app()
app.uninstall(bottle.JSONPlugin)
app.install(bottle.JSONPlugin(json_dumps=latci.json.dumps))


@route('/static/<path:path>')
def serve_static_files(path):
    return bottle.static_file(path, root='D:/git/listenandtalk/static/')


@route('/dbtest')
def dbtest(db):
    print(repr(db))


@route('/tokeninfo/<token>')
def token_info(db, token):
    import oauth2client.client
    from oauth2client.crypt import AppIdentityError

    print(repr(token))
    idinfo = oauth2client.client.verify_id_token(token, config.OAUTH2_CLIENT_ID)
    print(repr(idinfo))
    return idinfo
    if idinfo['aud'] != config.OAUTH2_CLIENT_ID:
        raise AppIdentityError("Unrecognized client ID.")
    if idinfo['iss'] not in config.OAUTH2_ISSUERS:
        raise AppIdentityError("Invalid issuer.")
    if config.OAUTH2_DOMAINS and idinfo['hd'] not in config.OAUTH2_DOMAINS:
        raise AppIdentityError("Domain not authorized.")
    if idinfo.get('exp', 0) < time.time():
        raise AppIdentityError("Token is expired.")


# Required for proper initialization of routes
import latci.views

bottle.run(host='0.0.0.0', port=8000, debug=True)
