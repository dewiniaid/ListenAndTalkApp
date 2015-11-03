from latci.api import rest
from latci.database import models
from latci.api.references import ScalarReferenceManager
from sqlalchemy import sql, orm


class SimpleIDRestController(rest.RESTController):
    url_instance = '<key:int>'

    @classmethod
    def create_manager(cls):
        return ScalarReferenceManager.from_controller(cls, column='id')

    @classmethod
    def setup(cls):
        super().setup()
        if not cls.model:
            return

        if getattr(cls, 'SchemaClass', None) is None:
            cls.SchemaClass = getattr(cls.model, 'SchemaClass')


# noinspection PyAbstractClass
class StudentRestController(SimpleIDRestController, rest.SortableRESTController, rest.InactiveFilterRESTController):
    model = models.Student
    name = 'student'

    allow_fetch = True
    allow_delete = False
    allow_delete_all = False
    allow_create = True
    allow_update = True
    allow_replace = False
    treat_put_as_patch = True
    sortable_columns = {v: [v] for v in ('name_first', 'name_last', 'id')}

    def get_schema(self):
        return self.SchemaClass(
            exclude=('id', 'enrollment'),
            dump_only=('date_inactive', 'date_created')
        )


# noinspection PyAbstractClass
class StaffRestController(SimpleIDRestController, rest.SortableRESTController, rest.InactiveFilterRESTController):
    model = models.Staff
    name = 'staff'

    allow_fetch = True
    allow_delete = False
    allow_delete_all = False
    allow_create = True
    allow_update = True
    allow_replace = False
    treat_put_as_patch = True
    sortable_columns = {v: [v] for v in ('name_first', 'name_last', 'id')}

    def get_schema(self):
        return self.SchemaClass(
            exclude=('id', 'activities'),
            dump_only=('date_inactive', 'date_created')
        )


# noinspection PyAbstractClass
class ActivityRestController(SimpleIDRestController, rest.SortableRESTController, rest.InactiveFilterRESTController):
    model = models.Activity
    name = 'activity'

    allow_fetch = True
    allow_delete = False
    allow_delete_all = False
    allow_create = True
    allow_update = True
    allow_replace = False
    treat_put_as_patch = True
    sortable_columns = {v: [v] for v in ('start_date', 'end_date', 'name')}  # TODO: Make more useful.

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.options['related'] = set(self.options.get('related', ['staff']))

    def query(self, ref=None, from_refresh=False):
        return super().query(ref, from_refresh).options(orm.lazyload('*'))

    def __call__(self):
        rv = super().__call__()
        if self is not self.root:
            return rv

        while self.related and not self.errors:
            self.related -= self.processed
            if not self.related:
                break
            refs_by_type = {}
            for ref in self.related:
                refs_by_type.setdefault(ref.manager.controller, set()).add(ref)
            for controller, refs in refs_by_type.items():
                refs = list(refs)
                c = controller(db=self.db, options={}, method='GET', ref=refs, data=None, params=None, auth=self.auth, root=self)
                result = c()
                rv.setdefault('related', []).extend(result['data'])
                self.processed.update(refs)

        return rv

    # def transform_out(self, ref, instance, value):
    #     ref = StaffRestController.manager.from_key(instance.staff_id)
    #     value['staff'] = StaffRestController.manager.from_key(instance.staff_id).to_dict()
    #     if 'staff' in self.options['related']:
    #         self.related.add(ref)
    #     return value
    #
    def get_schema(self):
        return self.SchemaClass(
            exclude=('id'),
            dump_only=('date_inactive', 'date_created')
        )

rest.setup_all()
