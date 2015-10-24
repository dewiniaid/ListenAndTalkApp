"""
Manages references.
"""
from abc import ABCMeta, abstractmethod
import sqlalchemy as sa


class AbstractReference(metaclass=ABCMeta):
    """
    Abstract reference base class.
    """
    manager = None

    @abstractmethod
    def __init__(self, *a, **kw):
        pass

    @classmethod
    @abstractmethod
    def from_model(cls, model):
        """Creates a reference from a model instance"""
        pass

    @abstractmethod
    def to_model(self, model):
        """Updates a model instance to match this reference"""
        pass

    @classmethod
    @abstractmethod
    def from_key(cls, key):
        pass

    @abstractmethod
    def to_key(self):
        """Returns a key representing this reference"""
        pass

    def to_dict(self, d=None, with_url=True, with_type=True):
        """Updates a dictionary (or returns a new one) to add fields representing this reference."""
        if d is None:
            d = {}
        d['key'] = self.to_key()
        if with_url:
            d['url'] = self.to_url()
        if with_type:
            d['type'] = self.manager.typename
        return d

    @classmethod
    def from_dict(cls, d):
        """Creates a reference from a dictionary"""
        return cls.from_key(d['key'])

    @abstractmethod
    def sql_equals(self):
        pass

    @classmethod
    @abstractmethod
    def sql_in(cls, refs):
        """
        Returns an SQL Expression that evaluates to True if a database object equals any of the references included in
        in refs"""
        pass

    def to_url(self):
        """
        Returns the URL for this reference.
        """
        makeurl = self.manager.makeurl
        if callable(makeurl):
            return makeurl(self.to_key())
        return makeurl.format(self.to_key())

    def __bool__(self):
        return True

    def __eq__(self, other):
        if isinstance(other, AbstractReference):
            return other.manager.typename == self.manager.typename and other.to_key() == self.to_key()


class ScalarReference(AbstractReference):
    """
    Refers to objects with a single 'value' attribute, as opposed to any composite form.
    """
    def __init__(self, value):
        self.value = value

    @classmethod
    def from_model(cls, model):
        """Creates a reference from an SQLAlchemy model"""
        return cls(getattr(model, cls.manager.column))

    def to_model(self, model):
        """Updates a model to match this reference"""
        setattr(model, self.manager.column, self.value)
        return model

    @classmethod
    def from_key(cls, key):
        """Creates a reference from a key"""
        return cls(key)

    def to_key(self):
        """Returns a key representing this reference"""
        return self.value

    def sql_equals(self):
        """Returns an SQL Expression that evaluates to True if a database object equals this reference."""
        return getattr(self.manager.modelclass, self.manager.column) == self.value

    @classmethod
    def sql_in(cls, refs):
        """
        Returns an SQL Expression that evaluates to True if a database object equals any of the references included in
        in refs"""
        if not refs:
            return sa.false
        if len(refs) == 1:
            return refs[0].sql_equals()
        return getattr(cls.manager.modelclass, cls.manager.column).in_(item.value for item in refs)


class ScalarReferenceManager:
    """Handles references."""
    def __init__(self, modelclass, typename, makeurl, column=None):
        """
        Handles converting and generating reference objects.

        :param modelclass: ORM Object Class
        :param typename: Unique type name.
        :param makeurl: URL format string or callback
        :param column: Database column name.  Autodetected if none.
        """
        if column is None:
            pk = sa.inspect(modelclass).primary_key
            if not pk or len(pk) != 1:
                raise ValueError("Primary key must have exactly 1 column for this ReferenceManager.")
            column = pk[0].key

        self.column = column
        self.modelclass = modelclass
        self.typename = typename
        self.makeurl = makeurl
        self.factory = type(typename + 'Reference', (ScalarReference,), {'manager': self})

        for method in 'from_model', 'from_key', 'from_dict', 'sql_in':
            setattr(self, method, getattr(self.factory, method))

    @classmethod
    def from_controller(cls, controller, *a, **kw):
        modelclass = kw.pop('modelclass', controller.model)
        typename = kw.pop('typename', controller.name)
        makeurl = kw.pop('makeurl', controller.url_base + "/{}")

        return cls(
            controller.model,
            controller.name,
            controller.url_base + "/{}",
            *a, **kw
        )
