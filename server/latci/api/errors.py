__author__ = 'Daniel'
import http.client


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
    fmt = None
    status = http.client.INTERNAL_SERVER_ERROR

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
            self.text = fmt.format(**self.params)
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

    def modify_response(self, response):
        response.status = self.status


class RequestNotAllowedError(APIError):
    status = http.client.METHOD_NOT_ALLOWED
    name = 'request-method-not-allowed'
    text = 'Request Method Not Allowed'


class JSONValidationError(APIError):
    status = http.client.BAD_REQUEST
    name = 'json-invalid-error'
    text = 'JSON Request Body is not expected here.'


class ValidationError(APIError):
    status = http.client.BAD_REQUEST
    name = 'validation-error'
    text = 'Validation error.'


class DatabaseIntegrityViolation(ValidationError):
    status = http.client.BAD_REQUEST
    name = 'integrity-violation'
    text = 'The requested action violates database integrity constraints.'


class MissingKeyError(APIError):
    status = http.client.BAD_REQUEST
    name = 'key-required'
    text = 'Data element must have a key.'


class MissingValueError(APIError):
    status = http.client.BAD_REQUEST
    name = 'value-required'
    text = 'Data element must have a value.'


class NotFoundError(APIError):
    status = http.client.NOT_FOUND
    name = 'not-found'
    text = 'Object(s) not found.'
