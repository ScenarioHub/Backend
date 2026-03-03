import uuid
import threading
import time  # 시간 지연을 위해 추가
from django.db import connection, transaction
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from api.auth.decorators import jwt_auth_optional

# 데모용으로 미리 준비된 시나리오 ID (DB에 있는 ID로 수정하세요)
DEMO_SCENARIO_ID = 247 

def demo_generation_logic(job_uuid):
    """
    백그라운드에서 5초간 상태를 변경하는 데모 전용 로직
    """
    try:
        # 1. 3초 동안 'generating' 상태 유지
        time.sleep(3)
        
        # 2. 2초 동안 'recording' 상태로 변경
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE generation_jobs SET status = %s WHERE job_uuid = %s",
                ['recording', job_uuid]
            )
        time.sleep(2)
        
        # 3. 최종 완료 및 미리 준비된 시나리오 데이터 연결
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE generation_jobs SET status = %s, scenario_id = %s WHERE job_uuid = %s",
                ['done', DEMO_SCENARIO_ID, job_uuid]
            )
    except Exception as e:
        print(f"Demo Thread Error: {e}")

@api_view(['POST'])
@jwt_auth_optional
@authentication_classes([])
@permission_classes([])
def start_generation(request):
    """시나리오 생성 시작 (데모 버전)"""
    description = request.data.get('description')
    map_id = request.data.get('mapId')
    job_uuid = str(uuid.uuid4())

    # 초기 상태 등록 (generating)
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO generation_jobs (job_uuid, status, description, map_id) VALUES (%s, %s, %s, %s)",
            [job_uuid, 'generating', description, map_id]
        )

    # 실제 생성 엔진 대신 데모 스레드 시작
    thread = threading.Thread(target=demo_generation_logic, args=(job_uuid,))
    thread.start()

    return Response({
        'status': 201,
        'message': {
            'jobId': job_uuid,
            'state': 'generating'
        }
    }, status=201)

# get_generating_state 함수는 기존 파일과 동일하게 유지하시면 됩니다.
# (DB에 업데이트된 status를 그대로 읽어오기 때문입니다.)