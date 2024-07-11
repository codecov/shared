from typing import Any

from shared.django_apps.core.models import Repository
from shared.orms import _is_django_model


class DjangoSQLAlchemyRepositoryWrapper:
    # Repository type can be a Django Repository | SQLAlchemy Repository - added Any to help with IDE typing
    @staticmethod
    def get_repo_owner(repository: Repository | Any):
        if _is_django_model(repository):
            return repository.author
        else:
            return repository.owner
