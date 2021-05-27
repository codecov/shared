import os
from itertools import product

from shared.config import get_config
from shared.encryption.selector import DEFAULT_ENCRYPTOR_CONSTANT, EncryptorDivider
from shared.encryption.standard import StandardEncryptor


def get_encryptor_from_configuration() -> EncryptorDivider:
    """Gets an EncryptorDivider capable of dealing with a bunch of possible keys

    First of all, if you don't know, we make an encryptor by concatenating a
        bunch of given secret strings in a special way to make a key

    Here is how it works (if you change something, please make the effort to update the docs):

    The customer will have, in their INSTALL YAML, the following:

    ```
        setup:
            encryption_secret: <their_legacy_encryption_secret"
            encryption:
                keys:
                    - code: abc
                      value: "higsgilasifgshrvwa_45h3!@#$$@#ds"
                    - code: jki
                      value: "bqwbdwagydics_49s"
                    - code: plo
                      value: "uhsfsaigaernjchu3987$565*w"
                write_key: jki
    ```

    Notice our `new_key_style` variable below. That's the place we can put new hardcoded keys if
        we evern need to reroll them again.

    Assume for a small moment that we have multiple hardcoded keys: v1, v2, v3, v4, v5

    Then our system will cross all those hardcoded keys with all the user-given keys.
        And will produce a new Encryptor with each pair. Meaning we will get 9 Encryptors:
        - (v1, abc) - by using the hardcoded key v1 and user-given key abc
        - (v1, jki) - by using the hardcoded key v1 and user-given key jki
        - (v1, plo)
        - (v2, abc)
        - (v2, jki)
        ...
        - (v4, plo)
        - (v5, abc)
        - (v5, jki)
        - (v5, plo)

    So, they key (v1, abc) will get a "identifier" v1_abc. Each identifier gets that one.
        So, everytime a specific Encyptor is used to generate a secret, we will prepend its
        identifier to the secret. So the final value of encoding a string with (v3, jki)
        will be "v3_jki::<somesecret>"

    With those values prepended, it's easy later to know which encryptor was used to generate what.
        So, all we have to do is to pick the encryptor with the same identifier as
        the encoded key gives.

    All the user has to do is to not change a key value after it is put in production. The same
        way they already can't change encryption_secret

    Then, our system will produce a special Encryptor for the legacy key (which, notice, is the
        only one that uses the envvar ENCRYPTION_SECRET). Everytime an encoded string arrive without
        an identifier, we will know it's a legacy one, and pick the legacy generator for it.

    Returns:
        EncryptorDivider: The encryption instance that will be used
    """
    new_key_style = {"v1": "%_#v^tjq*$ggfn!s+q6&6b01rnm$i(yz8&5imgvt=m0g_g$z%9"}
    current_hardcoded_key = "v1"
    legacy_encryptor = StandardEncryptor(
        get_config("setup", "encryption_secret", default=""),
        os.getenv("ENCRYPTION_SECRET", ""),
        "fYaA^Bj&h89,hs49iXyq]xARuCg",
    )
    mapping = {DEFAULT_ENCRYPTOR_CONSTANT: legacy_encryptor}
    user_given_encryption_secret_list = get_config(
        "setup", "encryption", "keys", default={}
    )
    user_given_encryption_secret_mapping = {}
    for el in user_given_encryption_secret_list:
        user_given_encryption_secret_mapping[el["name"]] = el["value"]
    for hardcoded_key_pair, user_key_pair in product(
        new_key_style.items(), user_given_encryption_secret_mapping.items()
    ):
        hardcoded_key_name, hardcoded_key_value = hardcoded_key_pair
        user_key_name, user_key_value = user_key_pair
        key_name = f"{hardcoded_key_name}_{user_key_name}"
        encryptor = StandardEncryptor(hardcoded_key_value, user_key_value)
        mapping[key_name] = encryptor
    user_key_to_use = get_config("setup", "encryption", "write_key")
    if user_key_to_use is None:
        key_to_use = DEFAULT_ENCRYPTOR_CONSTANT
    else:
        key_to_use = f"{current_hardcoded_key}_{user_key_to_use}"
    return EncryptorDivider(mapping, key_to_use)
