"""
JSON model description/definition using Marshmallow and friends.

Note that this is largely duplication of latci.db.models, but as the project evolves this serves as a sort of
compatibility layer between an evolving database schema and a fixed API version.

It might be neccessary to make a separate version 3 schema of this at some point, particularly if making
backwards-incompatible changes.
"""
import marshmallow_sqlalchemy


class SchemaOptions(marshmallow_sqlalchemy.ModelSchema.OPTIONS_CLASS): #, marshmallow_jsonapi.Schema.OPTIONS_CLASS):
    def __init__(self, meta):
        super().__init__(meta)
        if self.model is None:
            return

        if not getattr(meta, 'writable_pk', False):
            # Add primary keys to dump_only
            self.dump_only += tuple(col.name for col in self.model.__table__.primary_key.columns)


# noinspection PyAbstractClass
class Schema(marshmallow_sqlalchemy.ModelSchema): #, marshmallow_jsonapi.Schema):
    OPTIONS_CLASS = SchemaOptions
    # @marshmallow.pre_dump
    # def data_filter(self, obj):
    #     unloaded = sqlalchemy.inspect(obj).unloaded
    #     rv = {
    #         attr: getattr(obj, attr) for attr in self.fields.keys() if attr not in unloaded
    #     }
    #     return dict(rv)

