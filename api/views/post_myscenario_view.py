from django.db import connection
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# 팀 프로젝트 공통 데코레이터 임포트
from api.decorators import jwt_auth_required 

@swagger_auto_schema(
    method='get',
    operation_summary="내 시나리오 목록 조회",
    operation_description="직접 토큰을 입력하여 본인의 시나리오 목록을 조회합니다.",
    # upload_view.py와 동일하게 파라미터 직접 생성
    manual_parameters=[
        openapi.Parameter(
            "Authorization", 
            openapi.IN_HEADER, 
            description="입력 형식: Bearer <JWT 토큰>", 
            type=openapi.TYPE_STRING,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="조회 성공",
            examples={
                "application/json": {
                    "status": 200,
                    "message": [
                        {
                            "id": "1",
                            "title": "테스트 시나리오",
                            "summary": "설명입니다.",
                            "createdAt": "2026-01-27 23:59:59",
                            "downloadCount": 5
                        }
                    ]
                }
            }
        ),
        401: openapi.Response(
            description="인증 실패 (토큰 누락 또는 만료)",
            examples={"application/json": {"detail": "자격 인증 데이터가 제공되지 않았습니다."}}
        ),
        404: openapi.Response(
            description="데이터 없음",
            examples={"application/json": {"status": 404, "message": "404 Not Found"}}
        )
    }
)
@api_view(['GET'])
@jwt_auth_required           # 커스텀 인증 사용
@authentication_classes([])  # 기본 인증 해제
@permission_classes([])      # 기본 권한 해제
def my_scenario(request):
    # jwt_auth_required가 넣어준 user_id 사용
    user_id = int(request.user_id) 

    with connection.cursor() as cursor:
        query = """
            SELECT 
                CAST(id AS CHAR) AS id, 
                title, 
                description AS summary, 
                DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS createdAt,
                download_count AS downloadCount
            FROM posts 
            WHERE uploader_id = %s
            ORDER BY created_at DESC
        """
        cursor.execute(query, [user_id])
        
        columns = [col[0] for col in cursor.description]
        scenarios = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return Response({"status": 200, "message": scenarios}, status=status.HTTP_200_OK)