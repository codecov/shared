from shared.typings.oauth_token_types import OauthConsumerToken


def encode_token(token: OauthConsumerToken) -> str:
    # Different git providers encode different information on the oauth_token column.
    # Check decode_token function below.
    if not token.get("secret") and not token.get("refresh_token"):
        return token["key"]

    string_to_save = (
        token["key"]
        + f":{token['secret'] if token.get('secret') else ' '}"
        + (f':{token["refresh_token"]}' if token.get("refresh_token") else "")
    )
    return string_to_save


def decode_token(_oauth: str) -> OauthConsumerToken:
    """
    This function decrypts a oauth_token into its different parts.
    At the moment it does different things depending on the provider.

    - bitbucket
        Encodes the token as f"{key}:{secret}"
    - github
    - gitlab
        Encodes the token as f"{key}: :{refresh_token}"
        (notice the space where {secret} should go to avoid having '::', used by decode function)
    """
    token = {}
    colon_count = _oauth.count(":")
    if colon_count > 1:
        # Github + Gitlab  (post refresh tokens)
        token["key"], token["secret"], token["refresh_token"] = _oauth.split(":", 2)
        if token["secret"] == " ":
            # We remove the secret if it's our placeholder value
            token["secret"] = None
    elif colon_count == 1:
        # Bitbucket
        token["key"], token["secret"] = _oauth.split(":", 1)
    else:
        # Github + Gitlab (pre refresh tokens)
        token["key"] = _oauth
        token["secret"] = None
    return token
