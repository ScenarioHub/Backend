import os
import re
from django.http import StreamingHttpResponse
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

@swagger_auto_schema(
    method="get",
    operation_summary="시나리오 영상 재생",
    operation_description="시나리오 영상을 재생합니다.",
    responses={
        206: openapi.Response(
            description="다운로드 성공",
            examples={
                'video/mp4': {
                    "status": 206,
                    "data": "Binary data"
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
def stream_video(request, id):
    status = 200
    message = 'Success'
    
    try:
        # 1. DB 조회
        with connection.cursor() as cursor:
            cursor.execute("SELECT video_url, file_format FROM scenarios WHERE id = %s", [id])
            row = cursor.fetchone()
            # 데이터가 없으면 즉시 404 리턴
            if not row or not row[0]:
                status = 404            # 변수 업데이트
                return Response(
                    data = {
                        'message': '영상을 찾을 수 없음',
                        'status': status
                    }, 
                    status=status
                )
                
            linux_path = row[0]
        
        # 2. 파일 존재 확인
        if not os.path.exists(linux_path):
            status = 404
            message = '서버에 실제 영상 파일이 존재하지 않음'
            return Response(
                data ={
                    'message': message,
                    'status': status,
                      },
                status=status
            )

        # 3. 스트리밍 설정 (Range 처리)
        file_size = os.path.getsize(linux_path)
        range_header = request.META.get('HTTP_RANGE', None)
        
        byte1, byte2 = 0, None
        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                byte1 = int(match.group(1))
                if match.group(2):
                    byte2 = int(match.group(2))

        if byte2 is None:
            byte2 = file_size - 1
        length = byte2 - byte1 + 1

        def file_iterator(path, offset, chunk_size=8192):
            with open(path, 'rb') as f:
                f.seek(offset)
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    yield data

        # --- 스트리밍 성공 시에는 StreamingHttpResponse를 즉시 반환 ---
        response = StreamingHttpResponse(
            file_iterator(linux_path, byte1),
            status=206,
            content_type=f"video/mp4"       # 동영상 api이므로 고정
        )
        response['Content-Length'] = str(length)
        response['Content-Range'] = f'bytes {byte1}-{byte2}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        return response

    except Exception as e:
        if status == 200: 
            status = 500            # 만약 위에서 직접 status를 지정하지 않았다면 기본 500 처리: 의도되지 않은 에러를 통과시키는 경우 방지
        return Response(
            data={
                'status': status,
                'message': str(e),
                 },
            status=status
        )