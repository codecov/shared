from uuid import uuid4

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from shared.django_apps.codecov_auth.models import (
    Account,
    AccountsUsers,
    InvoiceBilling,
    OktaSettings,
    OktaUser,
    OrganizationLevelToken,
    Owner,
    OwnerProfile,
    SentryUser,
    Session,
    StripeBilling,
    TokenTypeChoices,
    User,
    UserToken,
)
from shared.encryption.oauth import get_encryptor_from_configuration
from shared.plan.constants import TrialStatus

encryptor = get_encryptor_from_configuration()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Faker("email")
    name = factory.Faker("name")
    terms_agreement = False
    terms_agreement_at = None
    customer_intent = "Business"


class OwnerFactory(DjangoModelFactory):
    class Meta:
        model = Owner
        exclude = ("unencrypted_oauth_token",)

    name = factory.Faker("name")
    email = factory.Faker("email")
    username = factory.Faker("user_name")
    service = "github"
    service_id = factory.Sequence(lambda n: f"{n}")
    updatestamp = factory.LazyFunction(timezone.now)
    plan_activated_users = []
    admins = []
    permission = []
    free = 0
    onboarding_completed = False
    unencrypted_oauth_token = factory.LazyFunction(lambda: uuid4().hex)
    cache = {"stats": {"repos": 1, "members": 2, "users": 1}}
    oauth_token = factory.LazyAttribute(
        lambda o: encryptor.encode(o.unencrypted_oauth_token).decode()
    )
    user = factory.SubFactory(UserFactory)
    trial_status = TrialStatus.NOT_STARTED.value


class SentryUserFactory(DjangoModelFactory):
    class Meta:
        model = SentryUser

    email = factory.Faker("email")
    name = factory.Faker("name")
    sentry_id = factory.LazyFunction(lambda: uuid4().hex)
    access_token = factory.LazyFunction(lambda: uuid4().hex)
    refresh_token = factory.LazyFunction(lambda: uuid4().hex)
    user = factory.SubFactory(UserFactory)


class OktaUserFactory(DjangoModelFactory):
    class Meta:
        model = OktaUser

    email = factory.Faker("email")
    name = factory.Faker("name")
    okta_id = factory.LazyFunction(lambda: uuid4().hex)
    access_token = factory.LazyFunction(lambda: uuid4().hex)
    user = factory.SubFactory(UserFactory)


class OwnerProfileFactory(DjangoModelFactory):
    class Meta:
        model = OwnerProfile

    owner = factory.SubFactory(OwnerFactory)
    default_org = factory.SubFactory(OwnerFactory)


class SessionFactory(DjangoModelFactory):
    class Meta:
        model = Session

    owner = factory.SubFactory(OwnerFactory)
    lastseen = timezone.now()
    type = Session.SessionType.API.value
    token = factory.Faker("uuid4")


class OrganizationLevelTokenFactory(DjangoModelFactory):
    class Meta:
        model = OrganizationLevelToken

    owner = factory.SubFactory(OwnerFactory)
    token = uuid4()
    token_type = TokenTypeChoices.UPLOAD


class GetAdminProviderAdapter:
    def __init__(self, result=False):
        self.result = result
        self.last_call_args = None

    async def get_is_admin(self, user):
        self.last_call_args = user
        return self.result


class UserTokenFactory(DjangoModelFactory):
    class Meta:
        model = UserToken

    owner = factory.SubFactory(OwnerFactory)
    token = factory.LazyAttribute(lambda _: uuid4())


class AccountFactory(DjangoModelFactory):
    class Meta:
        model = Account

    name = factory.Faker("name")


class AccountsUsersFactory(DjangoModelFactory):
    class Meta:
        model = AccountsUsers

    user = factory.SubFactory(UserFactory)
    account = factory.SubFactory(Account)


class OktaSettingsFactory(DjangoModelFactory):
    class Meta:
        model = OktaSettings

    account = factory.SubFactory(Account)
    client_id = factory.Faker("pyint")
    client_secret = factory.Faker("pyint")
    url = factory.Faker("pystr")


class StripeBillingFactory(DjangoModelFactory):
    class Meta:
        model = StripeBilling

    account = factory.SubFactory(Account)
    customer_id = factory.Faker("pyint")


class InvoiceBillingFactory(DjangoModelFactory):
    class Meta:
        model = InvoiceBilling

    account = factory.SubFactory(Account)
