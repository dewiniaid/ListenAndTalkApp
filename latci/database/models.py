"""
Defines classes corresponding to tables in the database.

NOTE: The schema here is not fully representative of the actual database.

Notably, stored procedures, triggers, indexes and foreign key constraints are not fully represented.
"""
from sqlalchemy import Column, ForeignKey, sql

# SQL Types
from sqlalchemy.types import *
from sqlalchemy.dialects.postgresql import INET  # IP Addresses (non-standard type)

# ORM
from sqlalchemy.orm import relationship, backref, mapper, configure_mappers
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
import sqlalchemy.event

import re
import datetime
from latci import config
import latci.schema


@as_declarative()
class Model():
    """
    Base class for all ORM Objects (which correspond to tables in the database.
    """
    # Allow lazy evalaution of schema internal property.
    @property
    def schema(self):
        if not hasattr(self, '_schema'):
            setattr(self, '_schema', self.SchemaClass(instance=self))
        return self._schema

    def dump(self, *args, **kwargs):
        return self.schema.dump(self, *args, **kwargs)

    def dumps(self, *args, **kwargs):
        return self.schema.dumps(self, *args, **kwargs)

    def load(self, *args, **kwargs):
        return self.schema.load(self, *args, **kwargs)

    def loads(self, *args, **kwargs):
        return self.schema.loads(self, *args, **kwargs)

    @declared_attr
    def __tablename__(cls):
        """
        Automatically determine the name of the underlying table this class represents.

        Converts camelCaseAndTitleCaseNames to lowercase+underscored by adding underscores before any uppercase
        characters (other than the first).  FooBar and fooBar both become foo_bar.
        :param cls: ORM class
        :return: Table name for SQL
        """
        return (cls.__name__[0] + re.sub("([A-Z])", "_\\1", cls.__name__[1:])).lower()

    def __json__(self):
        """Native support for JSON encoding database objects, v1"""
        return {
            c.name: getattr(self, c.name) for c in self.__table__.columns
        }

    @classmethod
    def generate(cls, json):
        return cls.SchemaClass().make_instance(json)


class LookupTable():
    """
    Mixin class that handles simple cases of lookup tables -- simple id+name columns.
    """
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(Text, nullable=False, index=True)


class UniqueLookupTable(LookupTable):
    """
    Mixin class that handles simple cases of lookup tables -- simple id+name columns.  Name is unique
    """
    # id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(Text, nullable=False, index=True, unique=True)


class TimestampMixin():
    date_created = Column(DateTime(timezone=True), default=sql.func.now())
    date_inactive = Column(DateTime(timezone=True), default=None)


class Student(Model, TimestampMixin):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name_first = Column(Text, nullable=False)
    name_last = Column(Text, nullable=False)


class Staff(Model, TimestampMixin):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name_first = Column(Text, nullable=False)
    name_last = Column(Text, nullable=False)
    email = Column(Text, nullable=True)
    can_login = Column(Boolean, nullable=False, default=True)
    last_ip = Column(INET())
    last_visited = Column(DateTime(timezone=True))


class Location(Model, UniqueLookupTable):
    pass


class Category(Model, UniqueLookupTable):
    pass


class AttendanceStatus(Model, UniqueLookupTable):
    pass


class Activity(Model, TimestampMixin):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(Text, nullable=False)

    staff_id = Column(Integer, ForeignKey('staff.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    staff = relationship('Staff', lazy='joined', backref=backref('activities'))
    location = relationship('Location', lazy='joined')
    category = relationship('Category', lazy='joined')


class ActivityEnrollment(Model):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    activity_id = Column(Integer, ForeignKey('activity.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('student.id'), nullable=False)

    start_date = Column(Date, nullable=False, default=sql.func.now())
    end_date = Column(Date, nullable=True)

    activity = relationship('Activity', backref=backref('enrollment', lazy=True))
    student = relationship('Student', backref=backref('enrollment', lazy=True))


class Attendance(Model):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    student_id = Column(Integer, ForeignKey('student.id'), nullable=False)
    activity_id = Column(Integer, ForeignKey('activity.id'), nullable=False)
    date = Column(Date, nullable=False)
    status_id = Column(Integer, ForeignKey('attendance_status.id'), nullable=False)
    comment = Column(Text, nullable=True)
    date_entered = Column(DateTime(timezone=True), nullable=False, default=sql.func.now())

    student = relationship('Student')
    activity = relationship('Activity')
    status = relationship('AttendanceStatus', lazy='joined')


class AttendanceUpsert(Model):
    """Virtual table."""
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    student_id = Column(Integer, ForeignKey('student.id'), nullable=False)
    activity_id = Column(Integer, ForeignKey('activity.id'), nullable=False)
    date = Column(Date, nullable=False)
    status_id = Column(Integer, ForeignKey('attendance_status.id'), nullable=False)
    comment = Column(Text, nullable=True)
    date_entered = Column(DateTime(timezone=True), nullable=False, default=sql.func.now())

    student = relationship('Student')
    activity = relationship('Activity')
    status = relationship('AttendanceStatus', lazy='joined')


# Automatically generate Marshmallow schemas from ORM Models.  Adapted from
# https://marshmallow-sqlalchemy.readthedocs.org/en/latest/recipes.html#automatically-generating-schemas-for-sqlalchemy-models
# and heavily modified.
@sqlalchemy.event.listens_for(mapper, 'after_configured')
def setup_schema():
    # noinspection PyProtectedMember
    for class_ in Model._decl_class_registry.values():
        if not hasattr(class_, '__tablename__'):
            continue  # Skip abstract classes that don't have an underlying table.

        if hasattr(class_, 'SchemaClass'):
            continue

        # if class_.__name__.endswith('Schema'):
        #     raise ModelConversionError(
        #         "For safety, setup_schema can not be used when a Model class ends with 'Schema'"
        #     )

        # Determine schema metaclass
        meta_base = getattr(class_, 'Meta', object)
        if meta_base is not object and hasattr(meta_base, 'model'):
            Meta = meta_base
        else:
            class Meta(meta_base):
                model = class_

        schema_class = type(
            "{}Schema".format(class_.__name__),  # Name of new class
            (latci.schema.Schema,),  # Subclasses
            {'Meta': Meta}  # Members
        )
        setattr(class_, 'SchemaClass', schema_class)

configure_mappers()
