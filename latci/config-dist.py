"""
Application configuration file.

To use, rename this file from config-dist.py to config.py and fill in the appropriate fields.
"""
# Prefix for API calls.  Ignore the 'v2'.
API_PREFIX = "/api/"

# Serve static files?  Disable this if it's being handled upstream.
SERVE_STATIC_FILES = True

# Path to connect to the database
DATABASE_PATH = "postgres://username:password@host.example.com:5432/database"
DATABASE_SCHEMA = "listenandtalk"
# Whether to echo queries.  Only set True for debugging.
DATABASE_ECHO = False

# Google Auth
# Get this information from the Google Developers Console
OAUTH2_CLIENT_ID = 'CLIENT_ID_HERE.apps.googleusercontent.com'
# Not sure this is needed for our implementation
OAUTH2_CLIENT_SECRET = ''

# Allowed issuers for OAuth2 responses
OAUTH2_ISSUERS = ['accounts.google.com', 'https://accounts.google.com']

# Allowed Google Apps domains for OAuth2 responses.  If 'None',  Google Apps domains aren't checked
# This is an optional additional level of security, since accounts must exist in the database anyways
OAUTH2_DOMAINS = None
# OAUTH2_DOMAINS = ['example.org']

# If this is a value other than None, an Auth result not in the database will authenticate to this staff
# rather than failing as an unauthorized user.
# Make this None in a production environment.
OAUTH2_DEBUG_STAFF_ID = None

# Set this to true to force authentication to be skipped, and identify as OAUTH2_DEBUG_STAFF_ID instead.
OAUTH2_DEBUG_NOLOGIN = False

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
EXCEPTION_HANDLING = 'full'
