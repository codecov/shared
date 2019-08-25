import hashlib
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from base64 import b64encode, b64decode


class StandardEncryptor(object):

    def __init__(self, *keys, iv=None):
        self.backend = default_backend()
        self.key = self.generate_key(*keys)
        self.bs = 16
        self.iv = iv

    def generate_key(self, *keys):
        joined = ''.join(keys)
        return hashlib.sha256(
            joined.encode()
        ).digest()

    def decode(self, string):
        string = b64decode(string)
        iv, to_decrypt = string[:16], string[16:]
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        return self.unpad(decryptor.update(to_decrypt) + decryptor.finalize()).decode()

    def encode(self, string):
        if self.iv is None:
            iv = os.urandom(self.bs)
        else:
            iv = self.iv
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        result = encryptor.update(self.pad(string).encode()) + encryptor.finalize()
        return b64encode(iv + result)

    def unpad(self, s):
        return s[:-ord(s[len(s)-1:])]

    def pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    def decrypt_token(self, oauth_token):
        _oauth = self.decode(oauth_token)
        token = {}
        if ':' in _oauth:
            token['key'], token['secret'] = _oauth.split(':', 1)
        else:
            token['key'] = _oauth
            token['secret'] = None
        return token


class EncryptorWithAlreadyGeneratedKey(StandardEncryptor):

    def generate_key(self, *keys):
        return keys[0]
