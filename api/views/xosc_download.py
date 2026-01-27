import os

from django.db import connection
from django.http import StreamingHttpResponse
from rest_framework.response import Response
from rest_framework.decorators import api_view

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

@swagger_auto_schema(
    method="get",
    operation_summary="시나리오 파일 다운로드",
    operation_description="시나리오 파일을 다운로드 합니다.",
    responses={
        200: openapi.Response(
            description="다운로드 성공",
            examples={
                'application/octet-stream': {
                    "status": 200,
                    "data": "download URL"
                },
            }
        ),
        404: openapi.Response(
            description="파일을 찾을 수 없음",
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
def download_file(request, id):
    # 1. DB에서 리눅스 절대 경로 조회
    with connection.cursor() as cursor:
        cursor.execute("SELECT file_url FROM scenarios WHERE id = %s", [id])
        row = cursor.fetchone()
        if not row:
            status = 404
            return Response(
                data={
                    'status': status,
                    'message': "404 Not Found"
                },
                status=status
            )
        linux_path = row[0]

    # 3. 외부 서버에 요청하여 파일을 스트리밍으로 전달
    try:
        f = open(linux_path, "rb")

        filename = os.path.basename(linux_path)
        response = StreamingHttpResponse(f, content_type="application/octet-stream")
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception:
        f.close()

        import traceback
        print(traceback.format_exc())
                

        return Response(
                data={
                    'status': status,
                    'message': "404 Not Found"
                },
                status=status
            )