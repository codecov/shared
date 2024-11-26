from unittest.mock import patch

import pytest
from django.test import TestCase, override_settings

from shared.django_apps.codecov_auth.models import Owner
from shared.django_apps.core.tests.factories import OwnerFactory
from shared.license import LicenseInformation
from shared.self_hosted.service import (
    LicenseException,
    activate_owner,
    activated_owners,
    admin_owners,
    can_activate_owner,
    deactivate_owner,
    disable_autoactivation,
    enable_autoactivation,
    is_activated_owner,
    is_admin_owner,
    is_autoactivation_enabled,
    license_seats,
)


@pytest.fixture
def dbsession(db):
    return db


@override_settings(IS_ENTERPRISE=True)
@patch("shared.self_hosted.service.get_config")
def test_admin_owners(mock_get_config, dbsession):
    owner1 = OwnerFactory(service="github", username="foo")
    OwnerFactory(service="github", username="bar")
    owner3 = OwnerFactory(service="gitlab", username="foo")

    mock_get_config.return_value = [
        {"service": "github", "username": "foo"},
        {"service": "gitlab", "username": "foo"},
    ]

    owners = admin_owners()
    assert list(owners) == [owner1, owner3]

    mock_get_config.assert_called_once_with("setup", "admins", default=[])


@override_settings(IS_ENTERPRISE=True)
def test_admin_owners_empty(dbsession):
    OwnerFactory(service="github", username="foo")
    OwnerFactory(service="github", username="bar")
    OwnerFactory(service="gitlab", username="foo")

    owners = admin_owners()
    assert list(owners) == []


@override_settings(IS_ENTERPRISE=True)
@patch("shared.self_hosted.service.admin_owners")
def test_is_admin_owner(admin_owners, dbsession):
    owner1 = OwnerFactory(service="github", username="foo")
    owner2 = OwnerFactory(service="github", username="bar")
    owner3 = OwnerFactory(service="gitlab", username="foo")

    admin_owners.return_value = Owner.objects.filter(pk__in=[owner1.pk, owner2.pk])

    assert is_admin_owner(owner1) == True
    assert is_admin_owner(owner2) == True
    assert is_admin_owner(owner3) == False
    assert is_admin_owner(None) == False


@override_settings(IS_ENTERPRISE=True)
def test_activated_owners(dbsession):
    user1 = OwnerFactory()
    user2 = OwnerFactory()
    user3 = OwnerFactory()
    OwnerFactory()
    OwnerFactory(plan_activated_users=[user1.pk])
    OwnerFactory(plan_activated_users=[user2.pk, user3.pk])

    owners = activated_owners()
    assert list(owners) == [user1, user2, user3]


@override_settings(IS_ENTERPRISE=True)
@patch("shared.self_hosted.service.activated_owners")
def test_is_activated_owner(activated_owners, dbsession):
    owner1 = OwnerFactory(service="github", username="foo")
    owner2 = OwnerFactory(service="github", username="bar")
    owner3 = OwnerFactory(service="gitlab", username="foo")

    activated_owners.return_value = Owner.objects.filter(pk__in=[owner1.pk, owner2.pk])

    assert is_activated_owner(owner1) == True
    assert is_activated_owner(owner2) == True
    assert is_activated_owner(owner3) == False


@override_settings(IS_ENTERPRISE=True)
@patch("shared.license.get_current_license")
def test_license_seats_not_specified(mock_get_current_license, dbsession):
    mock_get_current_license.return_value = LicenseInformation(is_valid=True)
    assert license_seats() == 0


@override_settings(IS_ENTERPRISE=True)
@patch("shared.self_hosted.service.activated_owners")
@patch("shared.self_hosted.service.license_seats")
def test_can_activate_owner(license_seats, activated_owners, dbsession):
    license_seats.return_value = 1

    owner1 = OwnerFactory(service="github", username="foo")
    owner2 = OwnerFactory(service="github", username="bar")
    owner3 = OwnerFactory(service="gitlab", username="foo")

    activated_owners.return_value = Owner.objects.filter(pk__in=[owner1.pk, owner2.pk])

    assert can_activate_owner(owner1) == True
    assert can_activate_owner(owner2) == True
    assert can_activate_owner(owner3) == False

    license_seats.return_value = 5

    assert can_activate_owner(owner1) == True
    assert can_activate_owner(owner2) == True
    assert can_activate_owner(owner3) == True


@override_settings(IS_ENTERPRISE=True)
@patch("shared.self_hosted.service.can_activate_owner")
def test_activate_owner(can_activate_owner, dbsession):
    can_activate_owner.return_value = True

    other_owner = OwnerFactory()
    org1 = OwnerFactory(plan_activated_users=[other_owner.pk])
    org2 = OwnerFactory(plan_activated_users=[])
    org3 = OwnerFactory(plan_activated_users=[other_owner.pk])
    owner = OwnerFactory(organizations=[org1.pk, org2.pk])

    activate_owner(owner)

    org1.refresh_from_db()
    assert org1.plan_activated_users == [other_owner.pk, owner.pk]
    org2.refresh_from_db()
    assert org2.plan_activated_users == [owner.pk]
    org3.refresh_from_db()
    assert org3.plan_activated_users == [other_owner.pk]

    activate_owner(owner)

    # does not add duplicate entry
    org1.refresh_from_db()
    assert org1.plan_activated_users == [other_owner.pk, owner.pk]
    org2.refresh_from_db()
    assert org2.plan_activated_users == [owner.pk]
    org3.refresh_from_db()
    assert org3.plan_activated_users == [other_owner.pk]


@override_settings(IS_ENTERPRISE=True)
@patch("shared.self_hosted.service.can_activate_owner")
def test_activate_owner_cannot_activate(can_activate_owner, dbsession):
    can_activate_owner.return_value = False

    other_owner = OwnerFactory()
    org1 = OwnerFactory(plan_activated_users=[other_owner.pk])
    org2 = OwnerFactory(plan_activated_users=[])
    owner = OwnerFactory(organizations=[org2.pk])

    with TestCase().assertRaises(LicenseException) as e:
        activate_owner(owner)
        assert e.message == "no more seats available"

    org1.refresh_from_db()
    assert org1.plan_activated_users == [other_owner.pk]
    org2.refresh_from_db()
    assert org2.plan_activated_users == []


@override_settings(IS_ENTERPRISE=True)
def test_deactivate_owner(dbsession):
    owner1 = OwnerFactory()
    owner2 = OwnerFactory()
    org1 = OwnerFactory(plan_activated_users=[owner1.pk, owner2.pk])
    org2 = OwnerFactory(plan_activated_users=[owner1.pk])
    org3 = OwnerFactory(plan_activated_users=[owner2.pk])

    deactivate_owner(owner1)

    org1.refresh_from_db()
    assert org1.plan_activated_users == [owner2.pk]
    org2.refresh_from_db()
    assert org2.plan_activated_users == []
    org3.refresh_from_db()
    assert org3.plan_activated_users == [owner2.pk]


@override_settings(IS_ENTERPRISE=True)
def test_autoactivation(dbsession):
    disable_autoactivation()

    owner1 = OwnerFactory(plan_auto_activate=False)
    owner2 = OwnerFactory(plan_auto_activate=False)
    assert is_autoactivation_enabled() == False

    owner1.plan_auto_activate = True
    owner1.save()
    assert is_autoactivation_enabled() == True

    owner2.plan_auto_activate = True
    owner2.save()
    assert is_autoactivation_enabled() == True


@override_settings(IS_ENTERPRISE=True)
def test_enable_autoactivation(dbsession):
    owner = OwnerFactory(plan_auto_activate=False)
    enable_autoactivation()
    owner.refresh_from_db()
    assert owner.plan_auto_activate == True


@override_settings(IS_ENTERPRISE=True)
def test_disable_autoactivation(dbsession):
    owner = OwnerFactory(plan_auto_activate=True)
    disable_autoactivation()
    owner.refresh_from_db()
    assert owner.plan_auto_activate == False


@override_settings(IS_ENTERPRISE=False)
def test_activate_owner_non_enterprise(dbsession):
    org = OwnerFactory(plan_activated_users=[])
    owner = OwnerFactory(organizations=[org.pk])

    with TestCase().assertRaises(Exception):
        activate_owner(owner)

    org.refresh_from_db()
    assert org.plan_activated_users == []


@override_settings(IS_ENTERPRISE=False)
def test_deactivate_owner_non_enterprise(dbsession):
    owner1 = OwnerFactory()
    owner2 = OwnerFactory()
    org1 = OwnerFactory(plan_activated_users=[owner1.pk, owner2.pk])
    org2 = OwnerFactory(plan_activated_users=[owner1.pk])
    org3 = OwnerFactory(plan_activated_users=[owner2.pk])

    with TestCase().assertRaises(Exception):
        deactivate_owner(owner1)

    org1.refresh_from_db()
    assert org1.plan_activated_users == [owner1.pk, owner2.pk]
    org2.refresh_from_db()
    assert org2.plan_activated_users == [owner1.pk]
    org3.refresh_from_db()
    assert org3.plan_activated_users == [owner2.pk]
