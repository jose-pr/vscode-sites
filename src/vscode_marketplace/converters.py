from semver.version import Version
from django.urls.converters import StringConverter

# from .utils import regex_as_string


class SemVerConverter(StringConverter):
    # regex = regex_as_string(Version._REGEX_OPTIONAL_MINOR_AND_PATCH)

    def to_python(self, value):
        return Version.parse(value)

    def to_url(self, value):
        return str(value)
