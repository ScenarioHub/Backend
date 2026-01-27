from django.db import connection
from rest_framework.response import Response
from rest_framework.decorators import api_view

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

@swagger_auto_schema(
    method="get",
    operation_summary="시나리오 상세 조회",
    operation_description="시나리오 ID로 시나리오 상세 정보를 조회합니다.",
    manual_parameters=[
        openapi.Parameter(
            "id",
            openapi.IN_PATH,
            description="Scenario ID",
            type=openapi.TYPE_INTEGER,
            required=True,
        )
    ],
    responses={
        200: openapi.Response(
            description="조회 성공",
            examples={
                'application/json': {
                    'status': 200,
                    'message': {
                        'id': 0,
                        'title': '어린이 주행 시나리오',
                        'createdAt': '2025-12-28 16:01:45',
                        'description': '어린이 보호구역에서 다양한 돌발 상황(도로 횡단, 차 사이에서 등장 등)을 포함한 시나리오입니다.',
                        'code': '<OpenSCENARIO>...</OpenSCENARIO>',
                        'tags': ['어린이', '안전', '센서'],
                        'stats': { 'downloads': 0, 'views': 0, 'likes': 0 },
                        'isBookmarked': False,
                        'file': { 'format': 'OpenSCENARIO', 'version': '1.2', 'size': 100},
                        'uploader': {
                            'name': 'user',
                            'uploaderId': 1,
                            'email': 'email@email.com',
                            'totalScenarios': 12
                        }
                    }
                }
            }
        ),
        404: openapi.Response(
            description="시나리오 없음",
            examples={
                'application/json': {
                    'status': 404,
                    'message': "404 Not Found"
                }
            }
        ),
    },
)
@api_view(['GET'])
def scenario_detail(request, id):
    try:
        cursor = connection.cursor()
        columns = ['id', 'title', 'description', 'created_at', 'code',
                   'file_format', 'file_version', 'file_size',
                   'stats_downloads', 'stats_views', 'stats_likes',
                   'uploader_name', 'uploader_initials', 'uploader_email', 'uploader_total_scenarios',
                   'tags']
        sql_query = f"SELECT {','.join(columns)} FROM view_scenario_details WHERE id = %s"     # 수정, 기존 방식은 url에 id를 직접 넣음, 지금은 파라미터로 처리
        cursor.execute(sql_query, [id]) 
        view = cursor.fetchone()
        view = {col: val for col, val in zip(columns, view)}
        view['tags'] = [tag.strip() for tag in view['tags'].split(',')] if view['tags'] else []
        
        sql_query = f"select id from users where email={view['uploader_email']}"
        cursor.execute(sql_query)
        uid = int(cursor.fetchone()[0])

        connection.commit()
        connection.close()
        
        message = {
            'id': view['id'],
            'title': view['title'],
            'createdAt': view['created_at'],
            'description': view['description'],
            'code': view['code'],
            'tags': view['tags'],
            'stats': { 'downloads': view['stats_downloads'], 'views': view['stats_views'], 'likes': view['stats_likes'] },
            'isBookmarked': False,
            'file': { 'format': view['file_format'], 'version': view['file_version'], 'size': view['file_size']},
            'uploader': {
                'name': view['uploader_name'],
                'uploaderId': uid, 
                'email': view['uploader_email'],
                'totalScenarios': view['uploader_total_scenarios']
            }
        }
    except Exception as e:
        connection.rollback()
        status = 404
        message = '404 Not Found'

        import traceback
        print(traceback.format_exc())
    else:
        status = 200
    finally:
        return Response(
            data={
                'status': status,
                'message': message
            },
            status=status
        )
