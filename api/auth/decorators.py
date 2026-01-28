import hashlib
from functools import wraps

import jwt
from django.conf import settings
from django.db import connection
from django.http import JsonResponse

def _is_jti_revoked(jti_or_token: str) -> bool:
    if not jti_or_token:
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM revoked_tokens WHERE jti = %s LIMIT 1", [jti_or_token])
            return cursor.fetchone() is not None
    except Exception:
        # If table missing or DB error, treat as not revoked (backwards compatible)
        return False


def jwt_auth_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')

        # # [확인 1] 헤더가 들어오는지 확인
        # print(f"\n--- [JWT DEBUG START] ---")
        # print(f"1. Authorization Header: {auth_header}")

        if not auth_header or not auth_header.startswith('Bearer '):
            print("❌ Error: Header missing or No 'Bearer ' prefix")
            return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)

        token = auth_header.split(' ')[1]

        try:
            # [확인 2] 사용 중인 시크릿 키 확인 (앞 5글자만)
            clean_key = settings.SECRET_KEY.strip("'").strip('"')
            # print(f"2. Using Secret Key (first 5): {clean_key[:5]}...")

            # [확인 3] 디코딩 시도
            payload = jwt.decode(token, clean_key, algorithms=['HS256'])
            request.user_id = payload.get('user_id')
            # print(f"3. Decode Success! User ID: {request.user_id}")

            # Check revoked jti or fingerprint (md5 of token) if jti missing
            jti = payload.get('jti')
            if jti:
                fingerprint = str(jti)
            else:
                fingerprint = hashlib.md5(token.encode()).hexdigest()
            if _is_jti_revoked(fingerprint):
                print("❌ Error: Token has been revoked")
                return JsonResponse({'error': '토큰이 무효화되었습니다.'}, status=401)

            # print(f"--- [JWT DEBUG END] ---\n")

        except jwt.ExpiredSignatureError:
            print("❌ Error: Token Expired")
            return JsonResponse({'error': '토큰 만료'}, status=401)
        except jwt.InvalidTokenError as e:
            # [확인 4] 실패 원인 출력
            print(f"❌ Error: {str(e)}")
            # print(f"--- [JWT DEBUG END] ---\n")
            return JsonResponse({'error': f'인증 실패: {str(e)}'}, status=401)

        return func(request, *args, **kwargs)

    return wrapper


def jwt_auth_optional(func):
    """Optional JWT decorator: if Authorization header with Bearer token is present,
    try to decode and set request.user_id. If absent or invalid, set request.user_id = None
    and continue without returning an error.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        # print(f"\n--- [JWT OPTIONAL DEBUG START] ---")
        # print(f"1. Authorization Header: {auth_header}")

        if not auth_header or not auth_header.startswith('Bearer '):
            # No token: continue as anonymous
            request.user_id = None
            print("No Authorization header or not Bearer - continuing as anonymous")
            # print(f"--- [JWT OPTIONAL DEBUG END] ---\n")
            return func(request, *args, **kwargs)

        token = auth_header.split(' ')[1]
        try:
            clean_key = settings.SECRET_KEY.strip("'").strip('"')
            # print(f"2. Using Secret Key (first 5): {clean_key[:5]}...")
            payload = jwt.decode(token, clean_key, algorithms=['HS256'])
            request.user_id = payload.get('user_id')

            # Check revoked jti and treat as anonymous if revoked
            jti = payload.get('jti')
            if jti:
                fingerprint = str(jti)
            else:
                fingerprint = hashlib.md5(token.encode()).hexdigest()
            if _is_jti_revoked(fingerprint):
                print("Token revoked - proceeding as anonymous")
                request.user_id = None
        except jwt.ExpiredSignatureError:
            print("Token expired - proceeding as anonymous")
            request.user_id = None
        except jwt.InvalidTokenError as e:
            print(f"Invalid token ({str(e)}) - proceeding as anonymous")
            request.user_id = None

        # print(f"--- [JWT OPTIONAL DEBUG END] ---\n")
        return func(request, *args, **kwargs)

    return wrapper
