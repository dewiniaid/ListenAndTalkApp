import sqlalchemy
import sqlalchemy.event
from sqlalchemy import orm, exc, sql

from latci import config

engine = sqlalchemy.create_engine(config.DATABASE_PATH, echo=True)

# @sqlalchemy.event.listens_for(engine, 'engine_connect')
# def set_schema_upon_connection(conn, _):
#     """Forces schema change upon a connection to the database."""
#     conn.execute("SET search_path={},public".format(config.DATABASE_SCHEMA))
#     conn.execute("COMMIT")


@sqlalchemy.event.listens_for(engine, 'checkout')
def set_schema_upon_connection(dbapi_conection, connection_record, connection_proxy):
    """Forces schema change upon a connection to the database."""
    cur = dbapi_conection.cursor()
    cur.execute("SET search_path={},public".format(config.DATABASE_SCHEMA))
    cur.execute("COMMIT")

Session = orm.sessionmaker(bind=engine, autocommit=False)

@sqlalchemy.event.listens_for(engine, "engine_connect")
def ping_connection(connection, branch):
    """Reduces the risk of connection resets due to pool timeouts."""
    # Shamelessly copied from http://docs.sqlalchemy.org/en/latest/core/pooling.html
    if branch:
        # "branch" refers to a sub-connection of a connection,
        # we don't want to bother pinging on these.
        return

    try:
        # run a SELECT 1.   use a core select() so that
        # the SELECT of a scalar value without a table is
        # appropriately formatted for the backend
        connection.scalar(sql.select[1])
    except exc.DBAPIError as err:
        # catch SQLAlchemy's DBAPIError, which is a wrapper
        # for the DBAPI's exception.  It includes a .connection_invalidated
        # attribute which specifies if this connection is a "disconnect"
        # condition, which is based on inspection of the original exception
        # by the dialect in use.
        if err.connection_invalidated:
            # run the same SELECT again - the connection will re-validate
            # itself and establish a new connection.  The disconnect detection
            # here also causes the whole connection pool to be invalidated
            # so that all stale connections are discarded.
            connection.scalar(sql.select([1]))
            print("Successfully resurrected a database connection.")
        else:
            raise
