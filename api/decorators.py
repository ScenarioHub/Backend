# decorators.py
import jwt
from django.conf import settings
from django.http import JsonResponse
from functools import wraps

def jwt_auth_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        # [확인 1] 헤더가 들어오는지 확인
        print(f"\n--- [JWT DEBUG START] ---")
        print(f"1. Authorization Header: {auth_header}")

        if not auth_header or not auth_header.startswith('Bearer '):
            print("❌ Error: Header missing or No 'Bearer ' prefix")
            return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)
        
        token = auth_header.split(' ')[1]
        
        try:
            # [확인 2] 사용 중인 시크릿 키 확인 (앞 5글자만)
            clean_key = settings.SECRET_KEY.strip("'").strip('"')
            print(f"2. Using Secret Key (first 5): {clean_key[:5]}...")
            
            # [확인 3] 디코딩 시도
            payload = jwt.decode(token, clean_key, algorithms=['HS256'])
            request.user_id = payload.get('user_id')
            print(f"3. Decode Success! User ID: {request.user_id}")
            print(f"--- [JWT DEBUG END] ---\n")
            
        except jwt.ExpiredSignatureError:
            print("❌ Error: Token Expired")
            return JsonResponse({'error': '토큰 만료'}, status=401)
        except jwt.InvalidTokenError as e:
            # [확인 4] 실패 원인 출력
            print(f"❌ Error: {str(e)}")
            print(f"--- [JWT DEBUG END] ---\n")
            return JsonResponse({'error': f'인증 실패: {str(e)}'}, status=401)
            
        return func(request, *args, **kwargs)
        
    return wrapper