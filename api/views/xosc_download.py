import os

from django.http import StreamingHttpResponse
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response

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
    with connection.cursor() as cursor:

        # DB에서 리눅스 절대 경로 조회
        cursor.execute("SELECT file_url FROM scenarios WHERE id = %s", [id])
        row = cursor.fetchone()
        if not row:
            status = 404
            return Response(
                data={
                    'status': status,
                    'message': "파일 정보가 DB에 없습니다."
                },
                status=status
            )
        linux_path = row[0]

        if not os.path.exists(linux_path):
                # 메시지를 "file_url이 잘못되었습니다"로 하셔도 무방합니다.
                return Response({'status': 404, 'message': "file_url이 잘못되었습니다. (파일 미존재)"}, status=404)

        # 다운로드 횟수(download_count) 1 증가 업데이트
        cursor.execute("UPDATE posts SET download_count = download_count + 1 WHERE id = %s", [id])
        connection.commit() # Raw SQL이므로 확정(commit) 필요
        
    # 3. 외부 서버에 요청하여 파일을 스트리밍으로 전달
    try:
        f = open(linux_path, "rb")

        filename = os.path.basename(linux_path)
        response = StreamingHttpResponse(f, content_type="application/octet-stream")
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return Response(
                data={'status': 500,
                  'message': f"파일 읽기 오류: {str(e)}"},
            status=500
            )