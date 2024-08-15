from django.db import models


def _is_django_model(object):
    return isinstance(object, models.Model)
