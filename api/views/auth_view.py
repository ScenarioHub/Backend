from types import SimpleNamespace

from django.shortcuts import render
from django.db import connection
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken

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
                        'initials': 'ex',
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

    # 기본 유효성 검사
    # 프론트 위임
    # if not email or not password or not name:
    #     return Response({"status": 400, "message": "필수 필드(email, password, name) 누락"}, status=status.HTTP_400_BAD_REQUEST)

    # if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
    #     return Response({"status": 400, "message": "이메일 형식이 올바르지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

    hashed_pw = make_password(password)

    try:
        with connection.cursor() as cursor:
            # 중복 이메일 검사
            cursor.execute("SELECT id FROM users WHERE email = %s", [email])
            if cursor.fetchone():
                return Response({"status": 400, "message": "이미 존재하는 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

            # users 테이블에 직접 INSERT (created_at, last_login_at은 NOW() 사용)
            cursor.execute(
                """
                INSERT INTO users (email, pass_hash, name, initials, provider_id, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                [email, hashed_pw, name, initials, None],
            )
            user_id = cursor.lastrowid
            connection.commit()

    except Exception as e:
        # 필요하면 로깅 추가
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
        last_login_at = timezone.now()

        # if not is_active:
        #     return Response({"status": 403, "message": "user is inactive"}, status=status.HTTP_403_FORBIDDEN)

        if not check_password(password, hashed_pw):
            return Response({"status": 401, "message": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # 서버 시간으로 로그인 시간 설정 (추가 SELECT 없이 동일한 값을 클라이언트에 반환)
        
        cursor.execute("UPDATE users SET last_login_at = %s WHERE id = %s", [last_login_at, user_id])
        try:
            connection.commit()
        except Exception:
            # 일부 DB 드라이버에서는 명시적 commit이 필요 없을 수 있음
            pass

        # 토큰 생성: 간단한 객체에 id 필드를 넣어 RefreshToken.for_user에 전달합니다.
        user_obj = SimpleNamespace(id=user_id, pk=user_id, email=email, name=name)
        refresh = RefreshToken.for_user(user_obj)
        # 추가 클레임 삽입
        refresh["email"] = email
        refresh["name"] = name
        access = refresh.access_token
        access["email"] = email
        access["name"] = name

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
        # 필요하면 로깅 추가

        import traceback
        print(traceback.format_exc())

        return Response({"status": 500, "message": "internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)