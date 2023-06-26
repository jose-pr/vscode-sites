from datetime import datetime
from typing import IO, Any
from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage

import requests

class FileInfo:
    mimetype:str 
    size: int
    modified: datetime


class HTTPStorage(Storage):
    def __init__(self, option=None):
        # if not option:
        #   option = settings.CUSTOM_STORAGE_OPTIONS
        pass
    def info(self, name:str):
        try:
            resp = requests.head(name)
            info = FileInfo()
            info.mimetype = resp.headers.get('content-type')
            info.size = resp.headers.get('content-length')
            info.modified = resp.headers.get('last-modififed')
            return info
        except:
            return None

    def url(self, name: str | None) -> str:
        return name

    def open(self, name: str, mode: str = ...) -> File:
        resp = requests.get(name, stream=True).raw
        resp.decode_content = True
        return resp

    def size(self, name: str) -> int:
        info = self.info(name)
        return info.size if info else 0
    
    def save(
        self, name: str | None, content: IO[Any], max_length: int | None = ...
    ) -> str:
        return super().save(name, content, max_length)
