from typing import Any

from shared.django_apps.codecov_auth.models import Owner
from shared.orms import _is_django_model


class DjangoSQLAlchemyOwnerWrapper:
    # Owner type can be a Django Owner | SQLAlchemy Owner - added Any to help with IDE typing
    @staticmethod
    def get_github_app_installations(owner: Owner | Any):
        if _is_django_model(owner):
            return owner.github_app_installations.all()
        else:
            return owner.github_app_installations

    # TODO: leaving as a template for the future in case it works
    # def template_thing_that_writes(self, owner):
    #     if self._is_django_model(owner):
    #         # stuff
    #         owner.save()
    #     else:
    #         db_session = owner.get_db_session()
    #         # stuff
    #         # TBD if we'd commit right away to follow sqlalchemy 'commit at the end'
    #         # db_session.commit()
