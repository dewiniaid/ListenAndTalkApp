import sqlalchemy
import sqlalchemy.event
import sqlalchemy.orm

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

Session = sqlalchemy.orm.sessionmaker(bind=engine, autocommit=False)

