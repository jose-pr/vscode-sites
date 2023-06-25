from typing import IO, Any
from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage

import requests

class HTTPStorage(Storage):
    def __init__(self, option=None):
        # if not option:
        #   option = settings.CUSTOM_STORAGE_OPTIONS
        pass

    def open(self, name: str, mode: str = ...) -> File:
        resp = requests.get(name, stream=True).raw
        resp.decode_content = True
        return resp


    def save(
        self, name: str | None, content: IO[Any], max_length: int | None = ...
    ) -> str:
        return super().save(name, content, max_length)
