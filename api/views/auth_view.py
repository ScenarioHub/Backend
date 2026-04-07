import hashlib
from datetime import datetime, timedelta

from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes, parser_classes, authentication_classes
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

@swagger_auto_schema(
    method="post",
    operation_summary="회원가입",
    operation_description="회원가입",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email", "password", "name"],
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
            "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            "name": openapi.Schema(type=openapi.TYPE_STRING),
        },
        example={
            "email": "example@example.com",
            "password": "example",
            "name": "홍길동",
        },
    ),
    responses={
        200: openapi.Response(
            description="조회 성공",
            examples={
                'application/json': {
                    'status': 200,
                    'message': {
                        'id': '0',
                        'email': 'example@example.com',
                    }
                }
            }
        ),
        404: openapi.Response(
            description="실패",
            examples={
                'application/json': {
                    'status': 404,
                    'message': "404 Not Found"
                }
            }
        ),
    },
)
@parser_classes([MultiPartParser, FormParser])
@api_view(["POST"])
def register(request):
    """
    Raw SQL 기반 회원가입 처리.
    필드: email, password, name, initials(optional)
    """
    data = request.data
    email = data.get("email").strip()
    password = data.get("password")
    name = data.get("name").strip()
    initials = "nm"

    hashed_pw = make_password(password)

    try:
        with connection.cursor() as cursor:
            # 중복 이메일 검사
            cursor.execute("SELECT id FROM users WHERE email = %s", [email])
            if cursor.fetchone():
                return Response({"status": 400, "message": "이미 존재하는 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

            # users 테이블에 직접 INSERT (created_at, last_login_at은 NOW() 사용)
            cursor.execute(
                # pgsql, now > current_timestamp
                """
                INSERT INTO users (email, pass_hash, name, initials, provider_id, created_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                [email, hashed_pw, name, initials, None],
            )
            # pgsql, lastrowid > returning id + fatchone
            user_id = cursor.fetchone()[0]  
            connection.commit()

    except Exception as e:
        connection.rollback()

        import traceback
        print(traceback.format_exc())

        return Response({"status": 500, "message": "회원가입 처리 중 DB 오류가 발생했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"status": 201, "message": {"id": user_id, "email": email, "name": name}}, status=status.HTTP_201_CREATED)

@swagger_auto_schema(
    method="post",
    operation_summary="로그인",
    operation_description="로그인",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email", "password", "name"],
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
            "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
        },
        example={
            "email": "example@example.com",
            "password": "example",
        },
    ),
    responses={
        200: openapi.Response(
            description="조회 성공",
            examples={
                'application/json': {
                    'status': 200,
                    'message': {
                        'access': 'token',
                        'refresh': 'token',
                        'lastLogin': '2026-01-23T16:09:05.012919Z',
                        'user':{
                            "email": 'example@example.com', 
                            "name": 'name'
                        }
                    }
                }
            }
        ),
        404: openapi.Response(
            description="실패",
            examples={
                'application/json': {
                    'status': 404,
                    'message': "404 Not Found"
                }
            }
        ),
    },
)
@parser_classes([MultiPartParser, FormParser])
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """
    Raw SQL 기반 로그인 처리.
    입력: { email, password }
    반환: { access, refresh, user: { id, email, name } }
    """
    data = request.data or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return Response({"status": 400, "message": "email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id, pass_hash, name FROM users WHERE email = %s", [email])
        row = cursor.fetchone()

        if not row:
            return Response({"status": 401, "message": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        user_id, hashed_pw, name = row

        # if not is_active:
        #     return Response({"status": 403, "message": "user is inactive"}, status=status.HTTP_403_FORBIDDEN)

        if not check_password(password, hashed_pw):
            return Response({"status": 401, "message": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # 서버 시간으로 로그인 시간 설정 (추가 SELECT 없이 동일한 값을 클라이언트에 반환)
        last_login_at = timezone.now()
        cursor.execute("UPDATE users SET last_login_at = %s WHERE id = %s", [last_login_at, user_id])
        
        connection.commit()

        # Create refresh token manually and persist to token_blacklist_outstandingtoken via raw SQL.
        refresh = RefreshToken()
        user_id_claim = settings.SIMPLE_JWT.get('USER_ID_CLAIM', 'user_id') if hasattr(settings, 'SIMPLE_JWT') else 'user_id'
        refresh[user_id_claim] = user_id
        refresh["email"] = email
        refresh["name"] = name
        access = refresh.access_token
        access["email"] = email
        access["name"] = name

        # compute expiry
        try:
            exp_ts = int(refresh.get('exp'))
            expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
        except Exception:
            rlt = None
            if hasattr(settings, 'SIMPLE_JWT') and isinstance(settings.SIMPLE_JWT, dict):
                rlt = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME')
            if rlt:
                expires_at = timezone.now() + rlt
            else:
                expires_at = timezone.now() + timedelta(days=7)

        # persist outstanding token (token text, jti, user_id)
        refresh_str = str(refresh)
        jti = str(refresh.get('jti'))
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO token_blacklist_outstandingtoken (token, created_at, expires_at, user_id, jti) VALUES (%s, %s, %s, %s, %s)",
                [refresh_str, timezone.now(), expires_at, user_id, jti]
            )
            connection.commit()

        return Response({
            "status": 200,
            "message": {
                "access": str(access),
                "refresh": str(refresh),
                "user": {"email": email, "name": name},
                "lastLogin": last_login_at
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        connection.rollback()

        import traceback
        print(traceback.format_exc())

        return Response({"status": 500, "message": "internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method="post",
    operation_summary="토큰 리프레시",
    operation_description="리프레시 토큰으로 새로운 액세스 토큰을 발급합니다.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["refresh"],
        properties={
            "refresh": openapi.Schema(type=openapi.TYPE_STRING),
        },
        example={"refresh": "<refresh_token>"},
    ),
    responses={
        200: openapi.Response(
            description="성공",
            examples={
                'application/json': {
                    'status': 200,
                    'message': {
                        'access': 'token',
                    }
                }
            }
        ), 
        401: openapi.Response(
            description="인증 실패",
            examples={
                'application/json': {
                    'status': 401,
                    'message': "401 invalid or expired refresh token"
                }
            }
        )
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    클라이언트가 보낸 refresh 토큰으로 새로운 access 토큰을 발급합니다.
    입력: { refresh }
    반환: { access }
    """
    data = request.data or {}
    token = data.get("refresh")

    if not token:
        return Response({"status": 400, "message": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        refresh = RefreshToken(token)
        access = refresh.access_token

        # If the client also sent the old access token in the Authorization header,
        # revoke it immediately so the old access cannot be used after a refresh.
        auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            old_access_token = auth_header.split(' ', 1)[1]
            old_access = AccessToken(old_access_token)
            old_jti = old_access.get('jti')
            # fingerprint: prefer jti if present, otherwise use md5(token)
            if old_jti:
                fingerprint = str(old_jti)
            else:
                fingerprint = hashlib.md5(old_access_token.encode()).hexdigest()
            # compute expires_at from token if available
            try:
                exp_ts = int(old_access.get('exp'))
                old_expires = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            except Exception:
                old_expires = None

            # create revoked_tokens table if not exists and insert jti
            with connection.cursor() as cursor:
                cursor.execute( 
                    # """
                    # CREATE TABLE IF NOT EXISTS revoked_tokens (
                    #     jti varchar(255) NOT NULL PRIMARY KEY,
                    #     token_type varchar(32),
                    #     revoked_at datetime(6) NOT NULL,
                    #     expires_at datetime(6) NULL,
                    #     user_id int NULL
                    # ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    # """ 
                    # pgsql
                    """ 
                    CREATE TABLE IF NOT EXISTS revoked_tokens (
                        jti varchar(255) NOT NULL PRIMARY KEY,
                        token_type varchar(32),
                        revoked_at timestamp(6) NOT NULL,
                        expires_at timestamp(6) NULL,
                        user_id int NULL
                    );
                    """
                )
                cursor.execute(
                    "INSERT INTO revoked_tokens (jti, token_type, revoked_at, expires_at, user_id) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE revoked_at = VALUES(revoked_at)",
                    [fingerprint, 'access', timezone.now(), old_expires, refresh.get(settings.SIMPLE_JWT.get('USER_ID_CLAIM', 'user_id'))]
                )
                connection.commit()

        # 필요하면 커스텀 클레임을 여기에 설정할 수 있습니다.
        return Response({"status": 200, "message": {"access": str(access)}}, status=status.HTTP_200_OK)

    except Exception:
        return Response({"status": 401, "message": "invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)


@swagger_auto_schema(
    method="post",
    operation_summary="로그아웃(리프레시 블랙리스트)",
    operation_description="클라이언트가 가진 리프레시 토큰을 블랙리스트 처리하여 더 이상 사용하지 못하게 합니다.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["refresh"],
        properties={"refresh": openapi.Schema(type=openapi.TYPE_STRING)},
        example={"refresh": "<refresh_token>"},
    ),
    responses={
        200: openapi.Response(
            description="성공",
            examples={
                'application/json': {
                    'status': 200,
                    'message': "logged out"
                }
            }
        ), 
        400: openapi.Response(
            description="잘못된 요청",
            examples={
                'application/json': {
                    'status': 400,
                    'message': "refresh token is required"
                }
            }
        )
    },
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def logout(request):
    """
    클라이언트가 제공한 refresh 토큰을 블랙리스트합니다. (로그아웃)
    입력: { refresh }
    """
    data = request.data or {}
    token = data.get("refresh")

    if not token:
        return Response({"status": 400, "message": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        refresh = RefreshToken(token)
        # token_blacklist 앱이 활성화되어 있으면 blacklist()를 호출합니다.
        # OutstandingToken 레코드가 없을 경우 예외가 발생할 수 있으므로 넓게 잡아 처리합니다.
        refresh.blacklist()

        # If the client sent the access token in Authorization header, revoke it as well.
        auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            old_access_token = auth_header.split(' ', 1)[1]
            from rest_framework_simplejwt.tokens import AccessToken

            old_access = AccessToken(old_access_token)
            old_jti = old_access.get('jti')
            if old_jti:
                fingerprint = str(old_jti)
            else:
                fingerprint = hashlib.md5(old_access_token.encode()).hexdigest()
            try:
                exp_ts = int(old_access.get('exp'))
                old_expires = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            except Exception:
                old_expires = None

            with connection.cursor() as cursor:
                cursor.execute( # pgsql
                    """
                    CREATE TABLE IF NOT EXISTS revoked_tokens (
                        jti varchar(255) NOT NULL PRIMARY KEY,
                        token_type varchar(32),
                        revoked_at timestamp(6) NOT NULL,
                        expires_at timestamp(6) NULL,
                        user_id int NULL
                    );
                    """
                )
                cursor.execute(
                    "INSERT INTO revoked_tokens (jti, token_type, revoked_at, expires_at, user_id) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE revoked_at = VALUES(revoked_at)",
                    [fingerprint, 'access', timezone.now(), old_expires, None]
                )
                connection.commit()

        return Response({"status": 200, "message": "logged out"}, status=status.HTTP_200_OK)

    except Exception:
        return Response({"status": 400, "message": "invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)