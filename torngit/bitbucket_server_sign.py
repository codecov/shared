import base64
import oauth2 as oauth
from tlslite.utils import keyfactory

PEM = """-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQC9d2iMTFiXglyvHmp5ExoNK2X8nxJ+1mlxgWOyTUpTrOKRiDUb
ZoZID3TP8CobQ5BsqDOSawHyi+Waf9Ca+iYoTu1fa8yZUreQXAdaK1u61Mn2XCkm
ITE/N5kvbYjDEWA1Dwb6CsvVkYZXo/Eq1X/3yrLXWKDNEnm0Cq48PFWqMQIDAQAB
AoGBAJ9wEqytuoeVDkXXhKXqayvV73cMrdXKvOTli24KGJgdjnQFeRtbxXhyeUxa
wDQ9QRYO3YdDQVpIW6kOEg+4nc4vEb4o2kiZTSq/OMkoO7NFM4AlsUbXB+lJ2Cgf
p0M4MjQVaMihvyXMw3qAFBNAAuwCYShau54rGTIbXJlODqN5AkEA4HPkM3JW8i11
xZLDYcwclYUhShx4WldNJkS0btoBwGrBt0NKiCR9dkZcZMLfFYuZhaLw5ybCw9dN
7iOiOoFexwJBANgYqhm0bQKWusSilD0mNmdq6HfSJsVOh5o/6GLsIEhPGkawAPkW
eReTr/Ucu+88a2QXo7GGjPRQxTY8UVcLl0cCQGO+nLbQJRtSYHgAlJstXbaEhxqs
ND/RdBOBjL2GXCjqSFPsr3542NhqxDxy7Thh5UOh+XR/oSXu1E7zvvBI9ZkCQECm
iGVuVFq8652eokj1ILuqAWivp8fJ6cndKtJFoJbhi5PwXionbgz+s1rawOMfKWXl
qKSZA5yoeYfzXcZ0AksCQQC3NtXZCOLRHvs+aawuUDyi0GmTNYgg3DNVP5vIUFRl
KyWKpbO+hG9eIqczRK4IxN89hoCD00GhRiWGqAVUGGhz
-----END RSA PRIVATE KEY-----"""

PRIVATEKEY = keyfactory.parsePrivateKey(PEM)


class _Signature(oauth.SignatureMethod):
    name = 'RSA-SHA1'

    def signing_base(self, request, consumer, token):
        if not hasattr(request, 'normalized_url') or request.normalized_url is None:
            raise ValueError("Base URL for request is not set.")

        sig = (
            oauth.escape(request.method),
            oauth.escape(request.normalized_url),
            oauth.escape(request.get_normalized_parameters()),
        )
        # ('POST', 'http%3A%2F%2Flocalhost%3A7990%2Fplugins%2Fservlet%2Foauth%2Frequest-token', 'oauth_consumer_key%3DjFzYB8pKJnz2BhaDUw%26oauth_nonce%3D15620364%26oauth_signature_method%3DRSA-SHA1%26oauth_timestamp%3D1442832674%26oauth_version%3D1.0')

        key = '%s&' % oauth.escape(consumer.secret)
        if token:
            key += oauth.escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def sign(self, request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.signing_base(request, consumer, token)

        signature = PRIVATEKEY.hashAndSign(raw)

        return base64.b64encode(signature)


signature = _Signature()
