import logging

from shared.encryption.token import decode_token

log = logging.getLogger(__name__)

DEFAULT_ENCRYPTOR_CONSTANT = "default_enc"


class EncryptorDivider(object):
    def __init__(self, encryptor_mapping, write_encryptor_code):
        self._encryptor_mapping = encryptor_mapping
        self.write_encryptor_code = write_encryptor_code
        if self.write_encryptor_code not in self._encryptor_mapping:
            log.error("Encryption does not seem to be properly configured")
            raise Exception("Encryption misconfigured on write code")

    def get_encryptor_from_code(self, code):
        return self._encryptor_mapping[code]

    def decode(self, string):
        if isinstance(string, bytes):
            string = string.decode()
        if "::" not in string:
            encryptor_code, code_to_decode = DEFAULT_ENCRYPTOR_CONSTANT, string
        else:
            encryptor_code, code_to_decode = string.rsplit("::", 1)
        encryptor_to_use = self.get_encryptor_from_code(encryptor_code)
        return encryptor_to_use.decode(code_to_decode)

    def encode(self, string):
        write_encryptor = self.get_encryptor_from_code(self.write_encryptor_code)
        result = write_encryptor.encode(string).decode()
        if self.write_encryptor_code != DEFAULT_ENCRYPTOR_CONSTANT:
            return f"{self.write_encryptor_code}::{result}".encode()
        return result.encode()

    def decrypt_token(self, oauth_token):
        _oauth: str = self.decode(oauth_token)
        return decode_token(_oauth)
