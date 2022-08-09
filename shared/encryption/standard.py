import hashlib
import os
from base64 import b64decode, b64encode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from shared.encryption.token import decode_token


class StandardEncryptor(object):
    def __init__(self, *keys, iv=None):
        self.backend = default_backend()
        self.key = self.generate_key(*keys)
        self.bs = 16
        self.iv = iv

    def generate_key(self, *keys):
        joined = "".join(keys)
        return hashlib.sha256(joined.encode()).digest()

    def decode(self, string):
        string = b64decode(string)
        iv, to_decrypt = string[:16], string[16:]
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        return self._unpad(decryptor.update(to_decrypt) + decryptor.finalize()).decode()

    def encode(self, string):
        if self.iv is None:
            iv = os.urandom(self.bs)
        else:
            iv = self.iv
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        result = encryptor.update(self._pad(string).encode()) + encryptor.finalize()
        return b64encode(iv + result)

    def _unpad(self, s):
        return s[: -ord(s[len(s) - 1 :])]

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    def decrypt_token(self, oauth_token):
        _oauth: str = self.decode(oauth_token)
        return decode_token(_oauth)


class EncryptorWithAlreadyGeneratedKey(StandardEncryptor):
    def generate_key(self, *keys):
        return keys[0]
