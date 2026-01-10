# api/views/xosc_download.py

import os
import requests     # pip install requests
from django.http import StreamingHttpResponse, Http404
from django.db import connection  # 모델 대신 DB 커넥션을 직접 사용
from rest_framework.decorators import api_view

@api_view(['GET'])
def download_file(request, id):
    # 1. DB에서 파일 경로 가져오기
    linux_file_path = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT file_url FROM scenarios WHERE id = %s", [id])
        row = cursor.fetchone()
        if row:
            linux_file_path = row[0]

    if not linux_file_path:
        print(f"❌ [에러] DB에서 ID {id}번을 찾을 수 없습니다.")
        raise Http404(f"ID {id}번 데이터가 없습니다.")

    # -------------------------------------------------------------
    # 2. 경로 변환 및 프록시 요청 준비
    # -------------------------------------------------------------
    
    # ★ 팀원에게 받은 외부 서버 주소 (IP와 포트 확인 필수!)
    # 예: "http://223.130.xxx.xxx:80" (끝에 슬래시 / 넣지 마세요)
    NGINX_SERVER_URL = "http://scenariohub.iptime.org:80" 

    # 경로 변환 로직
    # DB경로: /home/scenariohub/ScenarioHub/data/...
    # 웹경로: /media/... (Nginx 설정에 따라 다름)
    if linux_file_path.startswith('/home/scenariohub/ScenarioHub/data'):
        web_path = linux_file_path.replace('/home/scenariohub/ScenarioHub/data', '/media')
    else:
        web_path = linux_file_path
        
    # 최종 요청 URL
    target_url = f"{NGINX_SERVER_URL}{web_path}"

    # ★★★ [디버깅 로그] 터미널에서 이 부분을 꼭 확인하세요! ★★★
    print("-" * 60)
    print(f"🔍 [디버깅] 원래 DB 경로: {linux_file_path}")
    print(f"🔍 [디버깅] 변환된 URL:  {target_url}")
    print("-" * 60)

    # -------------------------------------------------------------
    # 3. 프록시 요청 (Django -> Nginx)
    # -------------------------------------------------------------
    try:
        # 3초 안에 연결 안 되면 에러 발생 (timeout=3)
        response = requests.get(target_url, stream=True, timeout=3)
        
        print(f"📡 [응답 상태코드] {response.status_code}") # 200이면 성공, 404면 경로 틀림

        if response.status_code != 200:
            print(f"❌ [실패] Nginx가 파일을 안 줍니다. 이유: {response.reason}")
            raise Http404(f"외부 서버 연결 실패 (코드: {response.status_code})")

        # 파일명 추출
        filename = os.path.basename(linux_file_path)
        
        # 스트리밍 응답 반환
        proxy_response = StreamingHttpResponse(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get('Content-Type', 'application/octet-stream')
        )
        # 한글 파일명 깨짐 방지 처리
        from urllib.parse import quote
        encoded_filename = quote(filename)
        proxy_response['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"
        
        return proxy_response

    except Exception as e:
        print(f"💥 [치명적 에러] {str(e)}")
        raise Http404("파일 다운로드 중 서버 내부 오류가 발생했습니다.")