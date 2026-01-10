import os, requests     # pip install requests
from django.http import StreamingHttpResponse, Http404
from django.db import connection
from rest_framework.decorators import api_view

@api_view(['GET'])
def download_file(request, id):
    # 1. DB에서 리눅스 절대 경로 조회
    with connection.cursor() as cursor:
        cursor.execute("SELECT file_url FROM scenarios WHERE id = %s", [id])
        row = cursor.fetchone()
        if not row: raise Http404("데이터 없음")
        linux_path = row[0]

    # 2. 외부 서버 URL로 변환 (Nginx 설정에 맞춤)
    base_url = "http://scenariohub.iptime.org"
    web_path = linux_path.replace('/home/scenariohub/ScenarioHub/data', '/media')
    target_url = f"{base_url}{web_path}"

    # 3. 외부 서버에 요청하여 파일을 스트리밍으로 전달
    try:
        resp = requests.get(target_url, stream=True, timeout=5)
        if resp.status_code != 200: raise Http404("파일 찾기 실패")

        response = StreamingHttpResponse(resp.iter_content(8192))
        filename = os.path.basename(linux_path)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception:
        raise Http404("서버 통신 오류")