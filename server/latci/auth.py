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
from sqlalchemy import orm, exc
from latci import config
from latci.database import models, Session
import random

import bottle
import functools
import collections.abc

import os

import base64
import json

def client_address(req = None):
    """
    Returns the client's IP address.
    :param req: Request object, defaults to bottle.request if None
    :return: IP address as string
    """
    if req is None:
        req = bottle.request

    ips = reversed(req.remote_route + [req.environ.get('REMOTE_ADDR')])
    for ip in ips:
        if ip not in config.AUTH_TRUSTED_PROXIES:
            return ip
    return ips[0]


class AuthSession():
    """
    Handles authentication

    :ivar is_valid: True if this session corresponds to a valid non-guest login.
    :ivar is_guest: True if this session corresponds to a valid guest login.
        This is true if none of the authentication parameters are present, or if the only parameters present
        correspond to a silent failure (e.g. expired session_id)
    :ivar session: Session attached to this result.
    :ivar error: Description of authentication error, if any.
    """

    cookie_params = {'name': 'session_id'}

    def __json__(self):
        rv = {}
        if self.session is not None:
            rv['session'] = self.session
            rv['expires'] = self.session.expires

        if self.error is not None:
            rv['error'] = self.error
            rv['status'] = 'error'

        elif self.is_valid:
            rv['status'] = 'ok'

        if self.error is not None or self.session is None:
            rv['oauth2-client-id'] = config.OAUTH2_CLIENT_ID

        return rv

    def __init__(self, token=None, session_id=None, db=None):
        """
        Creates a new AuthSession based on provided fields.

        Only one of (token, session_id, session) will be examined, based on the first non-None argument in that order.

        :param token: An id_token from Google Signin, or None
        :param session_id: A session ID, or none
        :param db: A database session, or None to None.
        :return:
        """
        self.is_valid = False
        self.is_guest = False
        #self.expires = None
        self.session = None
        self.error = None

        if db is None:
            db = Session()
        self.db = db

        if token is not None:
            self._parsetoken(token)
            return

        if session_id is not None:
            session = db.query(models.StaffSession).get(session_id)
            if session is None:
                self.error = 'Session expired.'
                return
        else:
            session = None
            self.error = 'Authentication required.'
            return

        self.session = session
        if not session.staff.can_login:
            self.error = "Account disabled."
        elif session.is_expired:
            self.error = "Session expired."
        else:
            self.is_valid = True
        return


    def _parsetoken(self, token):
        """Assists in validation of id_tokens from Google Signin"""
        try:
            idinfo = oauth2client.client.verify_id_token(token, config.OAUTH2_CLIENT_ID)
            print(repr(idinfo))
            if idinfo['aud'] != config.OAUTH2_CLIENT_ID:
                raise AppIdentityError("Unrecognized client ID.")
            if idinfo['iss'] not in config.OAUTH2_ISSUERS:
                raise AppIdentityError("Invalid issuer.")
            if config.OAUTH2_DOMAINS and idinfo['hd'] not in config.OAUTH2_DOMAINS:
                raise AppIdentityError("Domain not authorized.")
            if idinfo.get('exp', 0) < time.time():
                raise AppIdentityError("Token is expired.")
            if idinfo.get('email', None) is None:
                raise AppIdentityError("Email address not available.")
            self.email = idinfo['email']
            if not idinfo.get('email_verified', False):
                raise AppIdentityError("Email address not verified.")
        except AppIdentityError as e:
            self.error = e.args[0]
            return

        # If we're still here, Google says they're a valid user.  Let's check the database to see if they exist.
        try:
            staff = db.query(models.Staff).filter(models.Staff.email == self.email).one()
        except orm.exc.NoResultFound:
            staff = None
            if config.OAUTH2_DEBUG_STAFF_ID:
                try:
                    staff = db.query(models.Staff).get(config.OAUTH2_DEBUG_STAFF_ID)
                except orm.exc.NoResultFound:
                    staff = None
            if staff is None:
                self.error = 'Account not registered.'
                return result
        except orm.exc.MultipleResultsFound:
            raise Exception("Unexpected error (multiple accounts found)")

        if not staff.can_login:
            self.error = "Account disabled."
            return

        # Create a session
        self.session = create_session(staff)
        #self.expires = self.session.visited + datetime.timedelta(seconds=config.AUTH_SESSION_LIFETIME)
        #if config.AUTH_SESSION_MAXLIFETIME:
        #    self.expires = min(
        #        self.expires,
        #        self.session.created + datetime.timedelta(seconds=config.AUTH_SESSION_MAXLIFETIME)
        #    )
        self.is_valid = True
        return

    def set_cookie(self, response=None):
        if self.is_valid and self.session:
            response = bottle.response

        if self.session is None or not self.is_valid:
            return response.set_cookie(
                value='',
                max_age=-1, **self.cookie_params)
        return response.set_cookie(
            value=self.session.id,
            max_age=config.AUTH_COOKIE_LIFETIME, **self.cookie_params
        )

    @classmethod
    def create_from_request(cls, request=None, db=None):
        if request is None:
            request = bottle.request

        def _parse_dict(d):
            if not isinstance(d, collections.Mapping):
                return None

            token = d.get('id_token')
            session_id = d.get('session_id')

            if token:
                return cls(token=token, db=db)
            elif session_id:
                return cls(session_id=session_id, db=db)
            return None

        if isinstance(request.json, collections.Mapping):
            instance = _parse_dict(request.json['auth'])
            if instance:
                return instance

        authorization = bottle.request.get_header('Authorization')
        if authorization is not None:
            try:
                payload = json.loads(authorization)
                instance = _parse_dict(payload)
                if instance:
                    return instance
            except ValueError:
                pass

        session_id = request.cookies.get('session_id')
        if session_id is not None:
            return cls(session_id=session_id, db=db)

        return cls()

def create_session(staff, ip=None, db=None):
    """
    Creates a new StaffSession attached to the referenced staff person and returns it.

    :param staff: Staff to attach
    :param ip: IP address of creator.  Optional.
    :param db: Database handle.  Optional.
    :return: The new session.
    """
    if db is None:
        db = Session()

    if ip is None:
        ip = client_address()

    while True:
        # In practice, this loop should never execute more than once...
        # but just in case of the unlikely case of a hash collision, it loops
        try:
            db.rollback()
            id = str(base64.b85encode(os.urandom(config.AUTH_SESSION_KEYLEN)))
            print(repr(ip))
            session = models.StaffSession(
                id=id,
                staff_id=staff.id,
                origin_ip=ip,
                last_ip=ip
            )
            db.add(session)
            db.commit()
        except exc.IntegrityError as ex:
            db.rollback()
            # This odd exception handling is because it's not possible to tell the actual cause of the IntegrityError
            # It could also be that the referenced staff person does NOT exist
            if 'already exists' in ex.args[0]:
                continue  # Try again on next pass of the loop
            else:
                raise
        return db.query(models.StaffSession).filter(models.StaffSession.id == id).one()


def visit_session(session, ip=None, db=None):
    """
    'visits' a session -- updates last_ip and visited

    :param session: A StaffSession
    :param ip:
    :param db:
    :return: Updated session
    """
    if db is None:
        db = Session()
    if ip is None:
        ip = client_address()

    session.last_ip = ip
    session.visited = sql.func.now()
    db.rollback()
    db.add(session)
    db.commit()

    return db.query(models.StaffSession).filter(models.StaffSession.id == session.id).one()


def cleanup_sessions(db=None):
    """
    Cleans up expired sessions.

    :param db: Handle to db (optional)
    """
    if db is None:
        db = Session()

    return db.query(models.StaffSession).filter(models.StaffSession.is_expired).delete()


def maybe_cleanup_sessions(db=None):
    """
    Cleans up expired sessions based on config.AUTH_CLEANUP_FREQ
    :param db: Optional db handle
    :return: None, or the result of cleanup_sessions if cleanup occured.
    """
    if random.randint(0, config.AUTH_CLEANUP_FREQ) == 0:
        return cleanup_sessions(db)
    return None


def auth_wrapper(required=True, keyword=None, attach_json=True, fn=None):
    """
    Creates a wrapper for callables that service requests.

    :param required: True if valid authentication is required.  The underlying function will not be called if
        authentication fails
    :param keyword: Name of a keyword argument containing an AuthSession to pass to the wrapped function
    :param attach_json: If True and the wrapped function returns something dict-like, attach an auth: key to the dict
    :param fn: Optional parameter to avoid decorator syntax.
    :return:
    """
    def wrapper(fn):
        @functools.wraps(fn)
        def decorator(*args, **kwargs):
            db = kwargs.get('db', None)
            maybe_cleanup_sessions(db)
            auth = AuthSession.create_from_request(bottle.request, db)
            if auth.is_valid:
                auth.set_cookie(bottle.response)
                visit_session(auth.session)
            elif required:
                bottle.response.status = 403
                return {
                    'auth': auth,
                    'errors': [{'ref': None, 'text': 'Authentication required.'}]

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
