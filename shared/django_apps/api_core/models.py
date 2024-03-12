from django.db import models

from shared.django_apps.shared_core.models import Owner as SharedOwner


class Owner(SharedOwner):
    @property
    def get_name(self):
        return self.username

    class Meta:
        proxy = True
