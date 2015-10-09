"""
Defines classes corresponding to tables in the database.

NOTE: The schema here is not fully representative of the actual database.

Notably, stored procedures, triggers, indexes and foreign key constraints are not fully represented.
"""
from bottle.ext import sqlalchemy
from sqlalchemy import Column
from sqlalchemy import sql, orm, ForeignKey
from sqlalchemy.types import *
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base, declared_attr
import re


class _Model():
    """
    Base class for all ORM Objects (which correspond to tables in the database.
    """
    @declared_attr
    def __tablename__(cls):
        """
        Automatically determine the name of the underlying table this class represents.

        Converts camelCase and TitleCase to camel_case and title_case, respectively, by adding underscores before
        any uppercase characters (other than the first)
        :param cls: ORM class
        :return: Table name for SQL
        """
        return (cls.__name__[0] + re.sub("([A-Z])", "_\\1", cls.__name__[1:])).lower()
Model = declarative_base(cls=_Model)


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
    date_inactivated = Column(DateTime(timezone=True), default=sql.null)


class Student(Model, TimestampMixin):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name_first = Column(Text, nullable=False)
    name_true = Column(Text, nullable=False)



class Staff(Model, TimestampMixin):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name_first = Column(Text, nullable=False)
    name_true = Column(Text, nullable=False)

    email = Column(Text, nullable=True)
    can_login = Column(Boolean, nullable=False, default=True)


class Location(UniqueLookupTable):
    pass


class Category(UniqueLookupTable):
    pass


class AttendanceStatus(UniqueLookupTable):
    pass


class Activity(Model, TimestampMixin):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(Text, nullable=False)

    staff_id = Column(Integer, ForeignKey('staff.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    staff = relationship('Staff', lazy='joined')
    location = relationship('Location', lazy='joined')
    category = relationship('Location', lazy='joined')


class ActivityEnrollment(Model):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    activity_id = Column(Integer, ForeignKey('activity.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('activity.id'), nullable=False)

    start_date = Column(Date, nullable=False, default=sql.func.now())
    end_date = Column(Date, nullable=True)

    activity = relationship('Activity')
    student = relationship('Student')


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
    status = relationship('Status', lazy='joined')


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
    status = relationship('Status', lazy='joined')
