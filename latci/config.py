"""
Performs server configuration and sets default options.

To change the server configuration, don't alter this file.  Instead, set the appropriate environment variables
or modify server.ini

"""
import functools
import configparser
import os
import inspect

_our_path = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename))


# Prefix for API calls.  Ignore the 'v2'.
API_PREFIX = "/api/"

# Access-Control-Allow-Origin header override.  If empty, override will be unavailable.
API_ALLOWED_ORIGIN = []

# Serve static files?  Disable this if it's being handled upstream.
SERVE_STATIC_FILES = False

# Path to connect to the database
# DATABASE_PATH = ""
DATABASE_SCHEMA = "listenandtalk"

# Whether to echo queries.  Only set True for debugging.
DEBUG_SQL = False

# Google Auth
# Get this information from the Google Developers Console
# OAUTH2_CLIENT_ID = ''
# Not sure this is needed for our implementation
# OAUTH2_CLIENT_SECRET = 'gKnuI730DC0KsZmVg5H3PSj4'

# Allowed issuers for OAuth2 responses
OAUTH2_ISSUERS = ['accounts.google.com', 'https://accounts.google.com']

# Allowed Google Apps domains for OAuth2 responses.  If 'None',  Google Apps domains aren't checked
# This is an optional additional level of security, since accounts must exist in the database anyways
OAUTH2_DOMAINS = None

# If this is a value other than None, an Auth result not in the database will authenticate to this staff
# rather than failing as an unauthorized user.
# Make this None in a production environment.
DEBUG_LOGIN_AS = None

# Set this to true to force authentication to be skipped, and identify as OAUTH2_DEBUG_STAFF_ID instead.
DEBUG_SKIP_LOGIN = False

# When determining the IP address of a remote client, we ignore proxy servers with these IP addresses.
# This list should always include 127.0.0.1
AUTH_TRUSTED_PROXIES = {'127.0.0.1'}

# What 'realm' to present in the WWW-Authenticate header.  None means this field is not included.
AUTH_REALM = 'latci'

# How should the backend handle uncaught exceptions
# 'native' - Let the web framework do its normal thing with exceptions.
# 'silent' - Return 500 status with no explanation
# 'quiet' - Return 500 status with a JSON error response noting that an exception occured.
# 'normal' - Return 500 status with a JSON error response noting -which- exception occured.
# 'full' - Return 500 status with a JSON error response including full exception details.
# The default is 'normal'.  'full' should not be used in production environments.
# Unrecognized responses are treated as the default.
EXCEPTION_HANDLING = 'native'

# Where static files are located
STATIC_FILES_PATH = os.path.abspath(os.path.join(_our_path, "../client"))

def coerce_bool(v):
    if not isinstance(v, str):
        return bool(v)
    v = v.lower().strip()
    if v in ('y', 'yes', 't', 'true', 'on', '0'):
        return True
    if v in ('n', 'no', 'f', 'false', 'off', '1', ''):
        return False
    raise ValueError("Unable to coerce '{}' to a bool.", v)


def coerce_domainlist(v, cast=list):
    return cast(filter(None, (item.strip() for item in v.split(","))))


coerce_domainset = functools.partial(coerce_domainlist, cast=set)


# Options we support.
# Format is: attribute, coerce[, key]
# If key is omitted, it is the same as attribute.
options = [
    ('API_PREFIX', str),
    ('API_ALLOWED_ORIGIN', coerce_domainlist),
    ('SERVE_STATIC_FILES', coerce_bool),

    ('DATABASE_PATH', str),
    ('DATABASE_SCHEMA', str),
    ('OAUTH2_CLIENT_ID', str),
    ('OAUTH2_CLIENT_SECRET', str),
    ('OAUTH2_ISSUERS', coerce_domainset),
    ('OAUTH2_DOMAINS', coerce_domainset),
    ('AUTH_TRUSTED_PROXIES', coerce_domainset),
    ('AUTH_REALM', str),

    ('DEBUG_SQL', coerce_bool),
    ('DEBUG_SKIP_LOGIN', coerce_bool),
    ('DEBUG_LOGIN_AS', lambda x: None if not x else int(x)),
]

parser = configparser.ConfigParser()


# Try to find our INI file
if 'SERVER_CONFIG' in os.environ:
    parser.read(os.environ['SERVER_CONFIG'])
else:
    # Where are we?
    path = _our_path
    # Look at our path and up to 2 folders up for a server.ini file.
    for _ in range(3):
        filename = os.path.join(path, 'server.ini')
        if os.path.exists(filename):
            parser.read(filename)
            break
        path = os.path.join(path, "..")
    else:
        print('Warning: Could not find server.ini file.')


g = globals()
def _parse(attr, coerce, key=None):
    if key is None: key = attr
    value = os.environ.get(key)
    if value is None and parser is not None:
        try:
            value = parser.get('server', key)
        except (configparser.NoOptionError, configparser.NoSectionError):
            value = None

    if value is None:
        if attr not in g:
            raise ValueError("Setting {} is not configured and has no default value.".format(attr))
        return
    value = coerce(value)
    g[attr] = value
for option in options:
    _parse(*option)
