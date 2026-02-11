from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(
    method="get",
    operation_summary="전체 서비스 통계 데이터 조회",
    operation_description="공유된 시나리오 수, 활성 사용자 수, 총 다운로드 수의 합계를 가져옵니다.",
    responses={
        200: openapi.Response(
            description="조회 성공",
            examples={
                'application/json': {
                    "status": 200,
                    "message": {
                        "shared_scenarios": 2026,
                        "active_users": 2,
                        "total_downloads": 11
                    }
                }
            }
        ),
        404: openapi.Response(
            description="데이터를 찾을 수 없음",
            examples={
                'application/json': {
                    "status": 404,
                    "message": "통계 데이터를 집계하는 과정에서 오류가 발생했거나 데이터가 없습니다."
                }
            }
        ),
    }
)

@api_view(['GET'])
def get_scenario_stats(request):
    """
    Raw SQL을 이용한 서비스 통계 조회 API
    """
    # 단일 쿼리로 세 가지 데이터를 효율적으로 조회
    query = """
        SELECT 
            (SELECT COUNT(*) FROM posts) AS shared_scenarios,
            (SELECT COUNT(*) FROM users) AS active_users,
            (SELECT IFNULL(SUM(download_count), 0) FROM posts) AS total_downloads
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()

    # 데이터가 아예 없는 경우에 대한 예외 처리
    if not row:
        return Response({"status": 404, 
                         "message": "데이터 없음"}, 
                         status=404)

    # 데이터 매핑
    data = {
        "sharedScenarios": row[0],
        "activeUsers": row[1],
        "totalDownloads": int(row[2]), # Decimal 타입을 int로 변환
    }

    return Response({
            "status": 200,
            "message": data
        }, status=200)