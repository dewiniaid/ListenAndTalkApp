"""
Defines classes corresponding to tables in the database.

NOTE: The schema here is not fully representative of the actual database.

Notably, stored procedures, triggers, indexes and foreign key constraints are not fully represented.
"""
from sqlalchemy import Column, ForeignKey, sql, orm

# SQL Types
from sqlalchemy.types import *
from sqlalchemy.dialects.postgresql import INET  # IP Addresses (non-standard type)

# ORM
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

import re
import datetime

from latci import config


class _Model():
    """
    Base class for all ORM Objects (which correspond to tables in the database.
    """
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
        """Native support for JSON encoding database objects"""
        return {
            c.name: getattr(self, c.name) for c in self.__table__.columns
        }


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
    date_inactive  = Column(DateTime(timezone=True), default=None)


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
    category = relationship('Location', lazy='joined')


class ActivityEnrollment(Model):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    activity_id = Column(Integer, ForeignKey('activity.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('student.id'), nullable=False)

    start_date = Column(Date, nullable=False, default=sql.func.now())
    end_date = Column(Date, nullable=True)

    activity = relationship('Activity', backref=backref('enrollment'))
    student = relationship('Student', backref=backref('enrollment'))


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


class StaffSession(Model):
    """Tracks sessions"""
    id = Column(Text, primary_key=True, nullable=False)
    staff_id = Column(Integer, ForeignKey('staff.id'), nullable=False)

    created = Column(DateTime(timezone=True), nullable=False, default=sql.func.now())
    visited = Column(DateTime(timezone=True), nullable=False, default=sql.func.now())

    origin_ip = Column(INET, nullable=False)
    last_ip = Column(INET, nullable=False)

    staff = relationship('Staff', lazy='joined')

    # Helper properties for determining expiration time
    @hybrid_property
    def expires(self):
        expires = self.visited + datetime.timedelta(seconds=config.AUTH_SESSION_LIFETIME)
        if config.AUTH_SESSION_MAXLIFETIME:
            expires = min(expires, self.created + datetime.timedelta(seconds=config.AUTH_SESSION_MAXLIFETIME))
        return expires

    @expires.expression
    def expires(cls):
        if config.AUTH_SESSION_MAXLIFETIME:
            return sql.func.least(
                cls.visited + datetime.timedelta(seconds=config.AUTH_SESSION_LIFETIME),
                cls.created + datetime.timedelta(seconds=config.AUTH_SESSION_MAXLIFETIME)
            )
        return cls.visited + datetime.timedelta(seconds=config.AUTH_SESSION_LIFETIME)

    # Helper properties for determining whether an object is expired
    # Note: at the SQL level, is_expired is more efficient than comparing expires as it should allow indexes to
    # be used more optimally.
    @hybrid_property
    def is_expired(self):
        return self.expires < datetime.datetime.now()

    @is_expired.expression
    def is_expired(cls):
        now = sql.func.now
        seconds = lambda x: datetime.timedelta(seconds=x)
        cond = cls.visited < (now - seconds(config.AUTH_SESSION_LIFETIME))
        if config.AUTH_SESSION_MAXLIFETIME:
            cond |= (cls.created < (now - seconds(config.AUTH_SESSION_MAXLIFETIME)))
        return cond










