from typing import Any

from shared.django_apps.core.models import Repository
from shared.orms import ORMModelsMixins


class DjangoSQLAlchemyRepositoryWrapper(ORMModelsMixins):
    # Repository type can be a Django Repository | SQLAlchemy Repository - added Any to help with IDE typing
    def get_repo_owner(self, repository: Repository | Any):
        if self._is_django_model(repository):
            return repository.author
        else:
            return repository.owner
