"""
Handles authentication and authorization.

Authentication process in brief:

Clients may specify one of the following in requests:
a. A session_id, which corresponds to a row in a database sessions table
b. A id_token, which corresponds to a Google Signin Token

These may be specified as:
* A cookie named SessionID containing the appropriate payload, or
* In the 'auth' field of the JSON payload, e.g.
    auth: { session_id: "payload" }
    or auth: { id_token: "payload" }
* In the HTTP Authorization header as { session_id: "payload" } or { id_token: "payload" }

If we receive a LoginToken, we do the following:
* Authenticate it vs. Google to get an email address, or fail (invalid token)
* Validate the email address against a Staff entry, or fail (unauthorized)
* Check whether the Staff can_login or not, or fail (unauthorized - account disabled)
* Create a new SessionID with relevant expiry.
* Return that cookie back to the client in the 'auth' field in the request.

If we receive a SessionID, we do the following:
* Lookup the SessionID in the database
* Check to see if it's expired
* Return login information
"""
import oauth2client.client
from oauth2client.crypt import AppIdentityError
import time
from sqlalchemy import orm
from latci import config
from latci.database import models, Session
import latci.json

import bottle
import functools
import collections.abc
from latci.api.errors import APIError
import http.client
import datetime
import http.client


class RequiresAuthenticationError(APIError):
    name = 'authentication-required'
    text = 'Authentication required.'
    status = http.client.UNAUTHORIZED

    def modify_response(self, response, *, _attrs=None):
        super().modify_response(response)

        attrs = {} if _attrs is None else _attrs
        if config.AUTH_REALM and 'realm' not in attrs:
            attrs['realm'] = config.AUTH_REALM

        response.headers['WWW-Authenticate'] = (
            "Bearer " + ", ".join(
                k + '=' + latci.json.dumps(v) for k, v in attrs.items()
            )
        )
        return


class FailedAuthenticationError(RequiresAuthenticationError):
    name = 'authentication-failed'
    text = 'Authentication failed.'

    def __init__(self, hint=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hint = hint

    def __json__(self):
        rv = super().__json__()
        if self.hint:
            rv['hint'] = self.hint
        return rv

    def modify_response(self, response):
        return super().modify_response(
            response,
            _attrs={
                'error': 'invalid_token',
                'error_description': self.text
            }
        )


class ExpiredAuthenticationError(FailedAuthenticationError):
    name = 'authentication-expired'
    text = 'Authentication Expired.'


class UserNotAuthorizedError(FailedAuthenticationError):
    name = 'access-denied'
    text = None
    fmt = "Email address '{email}' is not authorized for this site."


def client_address(req=None):
    """
    Returns the client's IP address.
    :param req: Request object, defaults to bottle.request if None
    :return: IP address as string
    """
    if req is None:
        req = bottle.request

    ips = list(reversed(req.remote_route + [req.environ.get('REMOTE_ADDR')]))
    for ip in ips:
        if ip not in config.AUTH_TRUSTED_PROXIES:
            return ip
    return ips[0]


class AuthSession:
    """
    Handles authentication

    :ivar is_valid: True if this session corresponds to a valid non-guest login.
    :ivar is_guest: True if this session corresponds to a valid guest login.
        This is true if none of the authentication parameters are present, or if the only parameters present
        correspond to a silent failure (e.g. expired session_id)
    :ivar session: Session attached to this result.
    :ivar error: Description of authentication error, if any.
    """
    schema = models.Staff.SchemaClass(only=('email', 'name_first', 'name_last', 'id'))

    def __json__(self):
        rv = {
            'valid': self.is_valid,
            'guest': self.is_guest,
            'staff': None
        }
        if self.staff:
            rv['staff'] = self.staff  # self.schema.dump(self.staff).data
            rv['expires'] = self.expires
        else:
            rv['oauth2-client-id'] = config.OAUTH2_CLIENT_ID

        if self.error is not None:
            rv['error'] = self.error
        return rv

    def __init__(self, token=None, db=None):
        """
        Creates a new AuthSession based on provided fields.

        :param token: An id_token from Google Signin or another OAUTH2 provider, or None
        :param db: A database session, or None to create one.
        """
        if db is None:
            db = Session()
        self.db = db
        self.staff = None
        self.is_valid = False
        self.is_guest = True
        self.expires = None
        self.error = None

        if token is not None:
            try:
                staff = self.parse_token(token)
                staff.last_ip = client_address()
                staff.last_visited = datetime.datetime.now()
                db.add(staff)
                db.commit()
                self.staff = self.schema.dump(staff).data
                self.is_valid = True
                self.is_guest = False
                return
            except APIError as ex:
                self.error = ex

    def parse_token(self, token):
        """Assists in validation of id_tokens from Google Signin"""

        oauth_error = None

        # oauth2client's verify_id_token is nice and does a lot of validation for us, BUT... it's not particularly
        # detailed on the exceptions that it throws.  So if it fails, we retry the operation using the 'non-secure'
        # method and run it through our own checks.  If it somehow passes our own checks, we still treat it as a
        # failure and return the original failure message -- otherwise we return our own.
        try:
            idinfo = oauth2client.client.verify_id_token(token, config.OAUTH2_CLIENT_ID)
        except AppIdentityError as ex:
            oauth_error = ex
            try:
                idinfo = oauth2client.client._extract_id_token(token)
            except Exception as ex:
                raise FailedAuthenticationError("Failed to parse id_token.")
        if idinfo['aud'] != config.OAUTH2_CLIENT_ID:  # Is the token intended for us as an audience?
            raise FailedAuthenticationError("Unrecognized client ID.")
        if idinfo['iss'] not in config.OAUTH2_ISSUERS:  # Is it from an allowed issuer?
            raise FailedAuthenticationError("Invalid issuer.")
        if config.OAUTH2_DOMAINS and idinfo['hd'] not in config.OAUTH2_DOMAINS:
            raise FailedAuthenticationError("Domain not authorized.")
        exp = idinfo.get('exp', 0)
        if exp < time.time():
            raise ExpiredAuthenticationError("Token is expired.  Please request a new token.")
        self.expires = datetime.datetime.fromtimestamp(exp)
        email = idinfo.get('email')
        if email is None:
            raise FailedAuthenticationError("Email address not available.")
        if not idinfo.get('email_verified', False):
            raise FailedAuthenticationError("A verified email address is required.")

        # We see nothing wrong with the token on the surface, so if there was an oauth_error return it.
        if oauth_error:
            raise FailedAuthenticationError("Validation error: " + str(oauth_error))

        # If we're still here, Google says they're a valid user.  Let's check the database to see if they exist.
        try:
            query = self.db.query(models.Staff).filter(models.Staff.date_inactive.is_(None))
            if config.OAUTH2_DEBUG_STAFF_ID:
                staff = query.filter(models.Staff.id == config.OAUTH2_DEBUG_STAFF_ID).one()
            else:
                staff = query.filter(models.Staff.email == email).one()
        except orm.exc.NoResultFound:
            raise UserNotAuthorizedError(params={'email': email})
        return staff

    @classmethod
    def from_request(cls, request=None, db=None):
        if request is None:
            request = bottle.request

        if (
                isinstance(request.json, collections.abc.Mapping) and
                isinstance(request.json.get('auth'), collections.abc.Mapping)
        ):
            token = request.json['auth'].get('id_token')
            if token:
                return cls(token=token, db=db)

        auth = bottle.request.get_header('Authorization')
        if auth:
            auth = auth.split(' ', 2)
            if len(auth) == 2:
                if auth[0] == 'OAuth':
                    return cls(token=auth[1], db=db)
        return cls()


def auth_wrapper(required=True, keyword=None, attach_json=True, fn=None):
    """
    Creates a wrapper for callables that service requests.

    :param required: True if valid authentication is required.  The underlying function will not be called if
        authentication fails.
    :param keyword: Name of an optional keyword argument containing an AuthSession to pass to the wrapped function
    :param attach_json: If True and the wrapped function returns something dict-like, attach an auth: key to the dict
    :param fn: Optional parameter to avoid decorator syntax.
    :return:
    """
    def wrapper(fn):
        if config.OAUTH2_DEBUG_NOLOGIN:
            return fn

        @functools.wraps(fn)
        def decorator(*args, **kwargs):
            auth = AuthSession.from_request(bottle.request)
            if not auth.is_valid:
                if required and auth.error is None:
                    auth.error = RequiresAuthenticationError()
            if auth.error:
                auth.error.modify_response(bottle.response)
                return {
                    'auth': auth.__json__(),
                    'errors': [auth.error]
                }
            # Still here?  Call wrapped function
            rv = fn(*args, **kwargs)
            # Add JSON goodies
            if attach_json and isinstance(rv, dict):
                rv['auth'] = auth
            return rv
        return decorator
    if fn is None:
        return wrapper
    return wrapper(fn)
