from django.db import models


class Owner(models.Model):
    username = models.TextField()

    class Meta:
        app_label = "core"


# Create your models here.
