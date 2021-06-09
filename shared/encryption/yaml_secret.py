from shared.encryption.standard import EncryptorWithAlreadyGeneratedKey
from shared.encryption.selector import EncryptorDivider, DEFAULT_ENCRYPTOR_CONSTANT

yaml_secret_encryptor = EncryptorDivider(
    encryptor_mapping={
        DEFAULT_ENCRYPTOR_CONSTANT: EncryptorWithAlreadyGeneratedKey(
            b"]\xbb\x13\xf9}\xb3\xb7\x03)*0Kv\xb2\xcet"  # Same secret as in the main app
        ),
        "v1": EncryptorWithAlreadyGeneratedKey(
            b"\xc6f\x02\xf2Tg\x1d\xfa\x19\xe6\xc3<ky\xae\x0b"
        ),
    },
    write_encryptor_code=DEFAULT_ENCRYPTOR_CONSTANT,
)
