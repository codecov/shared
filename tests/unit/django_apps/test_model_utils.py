import pytest

from shared.django_apps.codecov_auth.tests.factories import OwnerFactory
from shared.django_apps.utils.model_utils import get_ownerid_if_member


class TestMigrationUtils:
    @pytest.mark.django_db(databases={"default"})
    def test_get_ownerid_if_member(self):
        test_owner_id = 123
        valid_owner_id = 456
        invalid_owner_id = 62139
        service = "github"
        username = "test-username"
        OwnerFactory(
            ownerid=test_owner_id,
            service=service,
            private_access=True,
            organizations=[valid_owner_id],
            username=username,
        )

        owner_id = get_ownerid_if_member(
            service=service, owner_username=username, owner_id=valid_owner_id
        )
        assert owner_id == test_owner_id

        null_owner_id = get_ownerid_if_member(
            service=service, owner_username=username, owner_id=invalid_owner_id
        )
        assert null_owner_id is None
