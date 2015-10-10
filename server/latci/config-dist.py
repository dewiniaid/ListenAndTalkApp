"""
Application configuration file.

To use, rename this file from config-dist.py to config.py and fill in the appropriate fields.
"""

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
OAUTH2_DEBUG_STAFF_ID = 1

# Lifetime for sessions in seconds.  Affects serverside database storage.  Renewed on every access.
AUTH_SESSION_LIFETIME = 60 * 60

# Absolute maximum session lifetime in seconds.  Sessions are terminated if they exist for more this duration.
AUTH_SESSION_MAXLIFETIME = 24 * 60 * 60

# Lifetime for session cookies in seconds.  This gets renewed at every request.  Set to None to have cookies expire
# immediately upon browser close.
AUTH_COOKIE_LIFETIME = AUTH_SESSION_LIFETIME

# Key length for session IDs in bytes.
AUTH_SESSION_KEYLEN = 16

# When determining the IP address of a remote client, we ignore proxy servers with these IP addresses.
# This list should always include 127.0.0.1
AUTH_TRUSTED_PROXIES = {'127.0.0.1'}

# The backend will periodically delete expired sessions from the database.
# Rather than existing as a scheduled task, this process runs about 1 in every N pageloads -- if those pageloads
# involve authorized clients.  There's no harm having expired sessions in the database other than disk space
# consumption and a tiny amount of performance, so this is safe to have fairly high.

AUTH_CLEANUP_FREQ = 100
