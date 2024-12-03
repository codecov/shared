from random import choice

from shared.django_apps.rollouts.models import RolloutUniverse


def default_random_salt():
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join([choice(ALPHABET) for _ in range(16)])


def rollout_universe_to_override_string(rollout_universe: RolloutUniverse):
    if rollout_universe == RolloutUniverse.OWNER_ID:
        return "override_owner_ids"
    elif rollout_universe == RolloutUniverse.REPO_ID:
        return "override_repo_ids"
    elif rollout_universe == RolloutUniverse.EMAIL:
        return "override_emails"
    elif rollout_universe == RolloutUniverse.ORG_ID:
        return "override_org_ids"
    else:
        return ""
