__author__ = 'Daniel'


class APIError(Exception):
    """
    Generic API Error class.

    Used to ensure consistent representation of errors, and allow raising them as exceptions.

    :ivar name: Name of this error, for front-end messaging.
    :ivar text: Text representation of error.
    :ivar params: Optional parameters to include.
    :ivar ref: Optional reference to object that caused the error.
    :ivar status: HTTP Status code (used in some cases)

    If name is None on the class and the exception does not specify a name, it defaults to self.__class__.__name__.
    """

    name = None
    status = 500

    def __init__(self, text=None, ref=None, name=None, fmt=None, status=None, params=None):
        """
        Initializes a new APIError

        All values (except ref and params) can be declared on the class or overridden on this constructor.

        :param text: English error text, already formatted.
        :param ref: Reference
        :param name: Name for this error.
        :param fmt: English error text as a format string that receives params.
        :param params:
        """
        self.params = params or []
        self.ref = ref

        if fmt is not None and text is not None:
            raise ValueError("text and fmt cannot both be set.")
        if fmt is None and text is None:
            fmt = self.__class__.fmt
            text = self.__class__.text
        if fmt:
            self.text = fmt.format(self.params)
        else:
            self.text = text
            if self.text is None:
                raise ValueError("text and fmt cannot both be None")
        if name is None:
            name = self.__class__.name
            if name is None:
                name = self.__class__.__name__
        self.name = name
        if status:
            self.status = status
        super().__init__(self.text)

    def __json__(self):
        d = {'text': self.text, 'name': self.name}
        if self.params:
            d['params'] = self.params

        if self.ref:
            d['ref'] = self.ref.to_dict()
        else:
            d['ref'] = None
        return d


class JSONValidationError(APIError):
    status = 400
    name = 'json-invalid-error'
    text = 'JSON Request Body is not expected here.'


class ValidationError(APIError):
    status = 400
    name = 'validation-error'
    text = 'Validation error.'


class MissingKeyError(APIError):
    status = 400
    name = 'key-required'
    text = 'Data element must have a key.'


class MissingValueError(APIError):
    status = 400
    name = 'value-required'
    text = 'Data element must have a value.'


class NotFoundError(APIError):
    status = 404
    name = 'not-found'
    text = 'Object(s) not found.'
