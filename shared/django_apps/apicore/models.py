import core.models as shared_core
from django.db import models


class ProxyOwner(shared_core.Owner):
    @property
    def some_property(self):
        return self.name

    class Meta:
        proxy = True


# Create your models here.
