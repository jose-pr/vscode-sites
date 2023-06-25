import datetime
import posixpath
from typing import Any, Callable
from django.db import models
from django.core.files.storage import Storage
from django.core.files.utils import validate_file_name


__all__ = []


# Create your models here.
class GenericStorageFieldFile(models.fields.files.FieldFile):
    field: "GenericStorageFileField"

    def __init__(self, instance: models.Model, field: "GenericStorageFileField", name):
        super(GenericStorageFieldFile, self).__init__(instance, field, name)
        self.storage = self.field.storage(self.field, self.instance)


class GenericStorageFileField(models.FileField):
    attr_class = GenericStorageFieldFile
    storage: Callable[["GenericStorageFileField", models.Model], Storage]

    def __init__(
        self,
        *args: Any,
        storage: Callable[["GenericStorageFileField", models.Model], Storage],
        **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.storage = storage

    def generate_filename(self, instance, filename):
        """
        Apply (if callable) or prepend (if a string) upload_to to the filename,
        then delegate further processing of the name to the storage backend.
        Until the storage layer, all file paths are expected to be Unix style
        (with forward slashes).
        """
        storage = self.storage(self, instance)
        if callable(self.upload_to):
            filename = self.upload_to(instance, filename)
        else:
            dirname = datetime.datetime.now().strftime(str(self.upload_to))
            filename = posixpath.join(dirname, filename)
        filename = validate_file_name(filename, allow_relative_path=True)
        return storage.generate_filename(filename)
    

__all__.append(GenericStorageFileField.__name__)
