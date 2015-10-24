from latci.api import rest
from latci.database import models
from latci.api.references import ScalarReferenceManager


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

    def get_schema(self):
        return self.SchemaClass(
            exclude=('id', 'enrollment', 'staff', 'location', 'category'),
            dump_only=('date_inactive', 'date_created')
        )


rest.setup_all()
