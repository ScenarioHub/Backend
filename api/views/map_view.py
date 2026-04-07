import mimetypes

from django.db import connection
from django.http import FileResponse
from rest_framework.response import Response
from rest_framework.decorators import api_view

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

@swagger_auto_schema(
    method='get',
    operation_summary="맵 목록 조회",
    operation_description="사용 가능한 맵을 조회합니다.",
    responses={
        200: openapi.Response(
            description="조회 성공",
            examples={
                'application/json': {
                    'status': 200,
                    'message': [
                        {
                            'id': 1,
                            'mapName': 'crest-curve',
                            'description': '',
                        },
                    ]
                }
            }
        )
    }
)
@api_view(['GET'])
def get_map_list(request):
    try:
        cursor = connection.cursor()

        columns = ['id', 'map_name', 'description', 'file_url', 'img_url']
        sql_query = f"SELECT * FROM maps"
        cursor.execute(sql_query)
        view = cursor.fetchall()
        view = [{col: val for col, val in zip(columns, view[i])} for i in range(len(view))]

        connection.commit()
        connection.close()

        message = [{
            'id': v['id'],
            'mapName': v['map_name'],
            'description': v['description'],
        }
            for v in view
        ]
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
    
@swagger_auto_schema(
    method="get",
    operation_summary="맵 미리보기 이미지 조회",
    operation_description="선택한 맵의 미리보기 이미지를 조회합니다.",
    manual_parameters=[
        openapi.Parameter(
            name="id",
            in_=openapi.IN_QUERY,
            description="맵 ID",
            type=openapi.TYPE_INTEGER,
            required=True,
            example=1,
        ),
    ],
    responses={
        200: openapi.Response(
            description='조회 성공',
            examples={
                'image/png': {
                    'status': 200,
                    'message': 'Binary data'
                }
            }
        ),
        400: openapi.Response(
            description='미리보기를 찾을 수 없음',
            examples={
                'application/json': {
                    'status': 404,
                    'message': "404 Not Found"
                }
            }
        )
    },
)
@api_view(['GET'])
def get_map_preview(request):
    map_id = request.GET.get("id", None)
    if map_id is None:
        return Response(data={'status': 400, 'message': '400 Bad Request'}, status=400)
    try:
        cursor = connection.cursor()
        sql_query = f"SELECT img_url FROM maps WHERE id={map_id}"
        cursor.execute(sql_query)
        img_url = cursor.fetchone()[0]

        connection.commit()
        connection.close()

        content_type, _ = mimetypes.guess_type(img_url)
        content_type = content_type or "application/octet-stream"

        # 4) FileResponse로 스트리밍 반환
        resp = FileResponse(open(img_url, "rb"), content_type=content_type)

        # 캐시(선택): 지도 이미지가 자주 안 바뀌면 매우 유용
        resp["Cache-Control"] = "public, max-age=86400"  # 1일 캐시 예시

        return resp
    except Exception as e:
        connection.rollback()
        status = 404
        message = '404 Not Found'

        import traceback
        print(traceback.format_exc())

        return Response(
            data={
                'status': status,
                'message': message
            },
            status=status
        )
    