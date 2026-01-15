import os
import re
from django.http import StreamingHttpResponse, Http404
from django.db import connection
from rest_framework.decorators import api_view

@api_view(['GET'])
def stream_video(request, id):
    # 1. DB에서 영상 파일의 절대 경로 조회
    with connection.cursor() as cursor:
        # id 파라미터를 사용하여 scenarios 테이블의 video_url 조회
        cursor.execute("SELECT video_url, file_format FROM scenarios WHERE id = %s", [id])
        row = cursor.fetchone()
        if not row or not row[0]:
            raise Http404("영상을 찾을 수 없음.")
        linux_path = row[0]
        file_format = row[1] if row[1] else 'mp4'

    # 2. 파일 존재 여부 확인
    try:
        if not os.path.exists(linux_path):
            raise Http404("서버에 실제 영상 파일이 존재하지 않음.")

        # 3. 스트리밍 및 Range 처리 (동영상 재생 핵심 로직)
        file_size = os.path.getsize(linux_path)             # 파일 크기
        range_header = request.META.get('HTTP_RANGE', None) # Range 헤더: 영상을 바이트단위의 청크로 요청하기 때문
        
        byte1, byte2 = 0, None
        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                byte1 = int(match.group(1))     # 시작 바이트
                if match.group(2):
                    byte2 = int(match.group(2)) # 끝 바이트

        if byte2 is None:
            byte2 = file_size - 1

        length = byte2 - byte1 + 1      # 실제로 전송할 조각의 길이

        # 파일을 조각내서 읽어주는 제너레이터
        def file_iterator(path, offset, chunk_size=8192):
            with open(path, 'rb') as f:
                f.seek(offset)      # 요청받은 시작점으로 포인터 이동
                while True:
                    data = f.read(chunk_size)   # 청크 단위로 읽기
                    if not data:
                        break
                    yield data

        # 4. StreamingHttpResponse 반환
        response = StreamingHttpResponse(
            file_iterator(linux_path, byte1),
            status=206,  # Partial Content (스트리밍 필수 상태코드)
            content_type=f"video/{file_format}"
        )

        response['Content-Length'] = str(length)                            # 실제 전송하는 바이트 길이
        response['Content-Range'] = f'bytes {byte1}-{byte2}/{file_size}'    # 현재 전송하는 바이트 범위
        response['Accept-Ranges'] = 'bytes'                                 # 바이트 단위의 범위 요청 지원
        
        return response
    except Exception as e:
        raise Http404("서버 통신 오류: ")