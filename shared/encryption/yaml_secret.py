from shared.config import get_config
from shared.encryption.selector import DEFAULT_ENCRYPTOR_CONSTANT, EncryptorDivider
from shared.encryption.standard import (
    EncryptorWithAlreadyGeneratedKey,
    StandardEncryptor,
)


def get_yaml_secret_encryptor():
    return EncryptorDivider(
        encryptor_mapping={
            DEFAULT_ENCRYPTOR_CONSTANT: EncryptorWithAlreadyGeneratedKey(
                b"]\xbb\x13\xf9}\xb3\xb7\x03)*0Kv\xb2\xcet"  # Same secret as in the main app
            ),
            "v1": EncryptorWithAlreadyGeneratedKey(
                b"\xc6f\x02\xf2Tg\x1d\xfa\x19\xe6\xc3<ky\xae\x0b"
            ),
            "v2": StandardEncryptor(
                "wM3UdcPC2zAGkk-qURHS9302YHXCcZo__HcLeQxz6PI",
                get_config(
                    "setup",
                    "encryption",
                    "yaml_secret",
                    default="YGUKnE-Ixm3lZINqBsMXKYN3shbGx_7_pYvKAUfdij4",
                ),
            ),
        },
        write_encryptor_code="v2",
    )


yaml_secret_encryptor = get_yaml_secret_encryptor()
