import hashlib

from django.db import connection
from rest_framework_simplejwt.authentication import JWTTokenUserAuthentication
from rest_framework.exceptions import AuthenticationFailed

class RevokedTokenAuthentication(JWTTokenUserAuthentication):
    """
    Extends the stateless JWTTokenUserAuthentication to check a lightweight
    `revoked_tokens` table (created on demand) for revoked token jtis. If a
    token's jti is present in the table, authentication fails.

    This uses raw SQL so we don't need to add a Django model + migration.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        # Determine fingerprint: prefer jti claim, otherwise use md5 of raw token
        try:
            raw_token_str = raw_token.decode() if isinstance(raw_token, (bytes, bytearray)) else str(raw_token)
        except Exception:
            raw_token_str = str(raw_token)

        jti = validated_token.get('jti')
        if jti:
            fingerprint = str(jti)
        else:
            fingerprint = hashlib.md5(raw_token_str.encode()).hexdigest()

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM revoked_tokens WHERE jti = %s LIMIT 1", [fingerprint])
                row = cursor.fetchone()
                if row:
                    raise AuthenticationFailed('Token has been revoked')
        except AuthenticationFailed:
            raise
        except Exception:
            # Any DB error (e.g., table missing) -> treat as not revoked.
            pass

        return self.get_user(validated_token), validated_token
