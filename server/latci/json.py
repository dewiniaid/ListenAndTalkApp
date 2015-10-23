"""
Minor overrides of JSON functions to support additional formats.

By using dump and dumps from this module, the following changes are made to JSON Output:

* Dates, Datetimes, and Times are output in ISO 8601 format.
* Objects with a __json__ attribute will use the json-encoded version of that attribute for JSON output.
  If the attribute is callable, it will be called first.
"""

import json
import datetime
import functools


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
            return o.isoformat()

        if hasattr(o, '__json__'):
            if callable(o.__json__):
                return o.__json__()
            return o.__json__
        return super().default(o)

dump = functools.partial(json.dump, cls=JSONEncoder)
dumps = functools.partial(json.dumps, cls=JSONEncoder)
load = json.load
loads = json.loads
