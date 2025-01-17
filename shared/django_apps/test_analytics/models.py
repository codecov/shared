from django.db import models

# Added to avoid 'doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS' error\
# Needs to be called the same as the API app
TEST_ANALYTICS_APP_LABEL = "test_analytics"


class Flake(models.Model):
    id = models.BigAutoField(primary_key=True)

    repoid = models.IntegerField()
    test_id = models.BinaryField()

    recent_passes_count = models.IntegerField()
    count = models.IntegerField()
    fail_count = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)

    class Meta:
        app_label = TEST_ANALYTICS_APP_LABEL
        db_table = "test_analytics_flake"
        indexes = [
            models.Index(fields=["repoid"]),
            models.Index(fields=["test_id"]),
            models.Index(fields=["repoid", "test_id"]),
            models.Index(fields=["repoid", "end_date"]),
        ]
