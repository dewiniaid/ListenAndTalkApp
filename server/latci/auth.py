"""
Handles authentication and authorization.

Authentication process in brief:

Clients may specify one of the following in requests:
a. A session_id, which corresponds to a row in a database sessions table
b. A id_token, which corresponds to a Google Signin Token

These may be specified as:
* A cookie ('SessionID' or 'Cookie' containing the appropriate payload, or
* In the 'auth' field of the JSON payload, e.g.
    auth: { session_id: "payload" }
    or auth: { id_token: "payload" }

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

import bottle
import functools
import collections.abc

import os

import base64

# Encode/decode session IDs
# encode_session_id takes one bytes argument as input and returns a safe string representation of it.
# decode_session_id takes one string argument as input and returns the original binary representation.
# decode_session_id(encode_session_id(orig)) == orig.
encode_session_id = base64.b85encode
decode_session_id = base64.b85decode

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


class AuthenticationResult():
    """
    Stores the result of any authentication attempts

    :ivar is_valid: True if the authentication result is valid (results in a succcesful non-guest login)
    :ivar is_guest: True if the authentication result is to treat this user as unauthenticated, but not as a failure
        This is true if none of the authentication parameters are present, or if the only parameters present
        correspond to a silent failure (e.g. expired session_id)
    :ivar staff: The referenced staff account, if known
    :ivar email: Referenced email address, if known
    :ivar expires: When the login expires.
    :ivar session_id: Session ID to maintain this session.  None if not present/invalid.
    :ivar id_token: ID token used to create this session.  None if not present/invalid
    :ivar error: Error message on failed auth.
    """

    def __init__(self):
        self.is_valid = False
        self.is_guest = False
        self.staff = None
        self.email = None
        self.expires = None
        self.session_id = None
        self.id_token = None
        self.reason = None
        pass


def create_session(staff, ip=None, db=None):
    if db is None:
        db = Session()

    if ip is None:
        ip = client_address()

    while True:
        # In practice, this loop should never execute more than once...
        # but just in case of the unlikely case of a hash collision, it loops
        try:
            db.rollback()
            id = os.urandom(config.AUTH_SESSION_KEYLEN)
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
            # It could also be that the referenced staff person does NOT exist.
            if 'already exists' in ex.args[0]:
                continue  # Try again on next pass of the loop
            else:
                raise

        return db.query(models.StaffSession).filter(models.StaffSession.id == id).one()


def check_token(token, db=None):
    if db is None:
        db = Session()

    result = AuthenticationResult()
    result.token = token
    # Sample code from https://developers.google.com/identity/sign-in/web/backend-auth, altered to our project
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
        result.email = idinfo['email']
        if not idinfo.get('email_verified', False):
            raise AppIdentityError("Email address not verified.")
        if not idinfo.get('email_verified', False):
            raise AppIdentityError("Email address not verified.")
    except AppIdentityError as e:
        result.reason = e.args[0]
        return result

    # If we're here, Google says they're a valid user.  Let's check the database...
    try:
        result.staff = db.query(models.Staff).filter(models.Staff.email == result.email).one()
    except orm.exc.NoResultFound:
        result.staff = None
        if config.OAUTH2_DEBUG_STAFF_ID:
            try:
                result.staff = db.query(models.Staff).get(config.OAUTH2_DEBUG_STAFF_ID)
            except orm.exc.NoResultFound:
                result.staff = None
        if result.staff is None:
            result.reason = 'Account not registered.'
            return result
    except orm.exc.MultipleResultsFound:
        raise Exception("Unexpected error (multiple accounts found)")

    if not result.staff.can_login:
        result.reason = "Account disabled."
        return result

    result.is_valid = True
    return result
