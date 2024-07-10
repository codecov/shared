from django.db import models


class ORMModelsMixins(object):
    def _is_django_model(self, object):
        return isinstance(object, models.Model)
