from django.db import models

# Added to avoid 'doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS' error
# Needs to be called the same as the API app
BUNDLE_ANALYSIS_APP_LABEL = "bundle_analysis_app"


class CacheConfig(models.Model):
    id = models.BigAutoField(primary_key=True)
    repo_id = models.IntegerField()
    bundle_name = models.CharField()
    is_caching = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_repo_bundle_pair",
                fields=["repo_id", "bundle_name"],
            )
        ]