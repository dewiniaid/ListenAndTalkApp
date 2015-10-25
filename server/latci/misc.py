"""
latci.misc - Miscellaneous code that doesn't have a better home yet.
"""
import bottle
import functools
import latci.config
import http.client

# How should the backend handle uncaught exceptions
# 'native' - Let the web framework do its normal thing with exceptions.
# 'silent' - Return 500 status with no explanation
# 'quiet' - Return 500 status with a JSON error response noting that an exception occurred.
# 'normal' - Return 500 status with a JSON error response noting -which- exception occurred.
# 'full' - Return 500 status with a JSON error response including full exception details.
# The default is 'normal'.  'full' should not be used in production environments.
# Unrecognized responses are treated as the default.
try:
    _exception_mode = latci.config.EXCEPTION_HANDLING
except AttributeError:
    _exception_mode = None

if _exception_mode not in('native', 'silent', 'quiet', 'normal', 'full'):
    _exception_mode = 'normal'


def wrap_exceptions(fn, mode=_exception_mode):
    """
    Catches most exceptions and wraps them into appropriate responses based on config.EXCEPTION_HANDLING
    :param fn: Function to wrap
    :return: Wrapped function

    Note that if EXCEPTION_HANDLING is native, this doesn't wrap the original function at all and returns it untouched.
    """
    if mode == 'native':
        return fn

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except bottle.HTTPResponse:
            raise
        except Exception as ex:
            import traceback
            print(traceback.format_exc())
            if mode == 'silent':
                bottle.abort(500, '')
                return  # Unreachable

            error = {
                'ref': None,
                'name': 'unexpected-exception',
                'text': 'An unexpected exception occured.'
            }
            if mode != 'quiet':
                error['exception'] = repr(ex.__class__)

                if mode == 'full':
                    error['backtrace'] = traceback.format_exc()

            bottle.response.status = http.client.INTERNAL_SERVER_ERROR
            return {'errors': [error]}

    return wrapper
