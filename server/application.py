import bottle
from bottle import route
# from bottle.ext import sqlalchemy
import bottle.ext.sqlalchemy
import latci.database

from latci import config
import latci.json

app = bottle.app()

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
import functools
runserver = functools.partial(bottle.run, host='0.0.0.0', port=8000, debug=True)

def cli_shell():
    """
    Command-line python shell functionality.
    :return:
    """
    import code
    import collections

    # Useful imports for CLI
    from latci.database import models, engine
    db = latci.database.Session()

    # Nasty hack, but needed.
    real_runserver = globals()['runserver']

    server_thread = None
    # docs_thread = None

    @functools.wraps(real_runserver)
    def runserver(*args, **kwargs):
        """
        Invokes bottle.run() with appropriate arguments.  Eats KeyboardInterrupt() exceptions so that they can be used to
        abort the running server without terminating the entire program.

        Intended for CLI use only.
        :return:
        """
        if server_thread:
            raise RuntimeError("Server thread is already running.")

        try:
            real_runserver(*args, **kwargs)
        except KeyboardInterrupt:
            pass

    def threadserver(*args, **kwargs):
        """
        Performs runserver() in a separate thread.  All arguments are passed to runserver().

        Intended for CLI use only.

        :return: Thread that runserver() is running in.
        """
        nonlocal server_thread
        if server_thread:
            raise RuntimeError("Server thread is already running.")

        import threading
        server_thread = threading.Thread(target=functools.partial(runserver, *args, **kwargs), daemon=True)
        server_thread.run()
        return server_thread

    print('Invoking latci shell.')
    print('Enter runserver() to invoke the embedded webserver.')
    print('Enter threadserver() to invoke the embedded webserver in a separate thread.')
    # print('Enter docserver() to invoke the local documentation server in a browser.')
    code.interact(local=dict(collections.ChainMap(locals(), globals())))
    return 0

def cli_docs():
    """
    CLI option for invoking pydoc.
    """
    import pydoc
    pydoc.browse()
    return 0

def main(argv):
    """
    Main entry point.
    """
    # Uninstall the JSON plugin Bottle installs by default, and add one configured the way we want.
    app = bottle.app()
    app.uninstall(bottle.JSONPlugin)
    app.install(bottle.JSONPlugin(json_dumps=functools.partial(latci.json.dumps, indent=True)))

    # Install SQLAlchemy plguin
    app.install(
        bottle.ext.sqlalchemy.Plugin(
            latci.database.engine, # SQLAlchemy engine created with create_engine function.
            None, # SQLAlchemy metadata, required only if create=True.
            keyword='db', # Keyword used to inject session database in a route (default 'db').
            create=False, # If it is true, execute `metadata.create_all(engine)` when plugin is applied (default False).
            commit=False, # If it is true, plugin commit changes after route is executed (default True).
            use_kwargs=True # If it is true and keyword is not defined, plugin uses **kwargs argument to inject session database (default False).
        )
    )

    import sys
    if 'shell' in sys.argv:
        sys.exit(cli_shell())
    elif 'docs' in sys.argv:
        sys.exit(cli_docs())
    runserver()

if __name__ == '__main__':
    import sys
    main(sys.argv)
