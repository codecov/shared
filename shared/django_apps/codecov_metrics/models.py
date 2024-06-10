from django.db import models

# Added to avoid 'doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS' error\
# Needs to be called the same as the API app
CODECOV_METRICS_APP_LABEL = "codecov_metrics"


class UserOnboardingLifeCycleMetrics(models.Model):
    id = models.BigAutoField(primary_key=True)
    org_id = models.IntegerField()
    event = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
