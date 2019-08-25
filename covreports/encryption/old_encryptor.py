"""Old encryptor based on pycrypto

JUST KEEPING THIS TO MAKE SURE THE NEW CRYPTOGRAPHY PACKAGE IS DOING THE SAME
"""

import hashlib

from Crypto import Random
from Crypto.Cipher import AES
from base64 import b64encode, b64decode


class OldEncryptor(object):

    def __init__(self, *keys, iv=None):
        self.joined = ''.join(keys)
        self.key = hashlib.sha256(
            self.joined.encode()
        ).digest()
        self.bs = 16
        self.iv = iv

    def decode(self, string):
        string = b64decode(string)
        iv = string[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self.unpad(cipher.decrypt(string[16:])).decode()

    def encode(self, string):
        if self.iv is None:
            iv = Random.new().read(AES.block_size)
        else:
            iv = self.iv
        des = AES.new(self.key, AES.MODE_CBC, iv)
        return b64encode(iv + des.encrypt(self.pad(string).encode()))

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
