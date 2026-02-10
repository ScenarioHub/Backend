import uuid
import threading

from django.db import connection
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from api.decorators import jwt_auth_optional
from utils.tasks import thread_start_generation


@swagger_auto_schema(
    method="post",
    operation_summary="시나리오 생성 시작",
    operation_description=(
        "자연어 설명과 map_id를 받아 시나리오 생성 작업(job)을 생성합니다."
        " 서버는 비동기 작업으로 `generator(description, map_id)`를 호출해야 합니다."
    ),
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['description', 'mapId'],
        properties={
            'description': openapi.Schema(type=openapi.TYPE_STRING, description='시나리오에 대한 자연어 설명'),
            'mapId': openapi.Schema(type=openapi.TYPE_INTEGER, description='선택한 맵의 ID'),
        }
    ),
    responses={
        201: openapi.Response(
            description="생성 작업 등록됨",
            examples={
                'application/json': {
                    'status': 201,
                    'message': {
                        'jobId': 'uuid',
                        'status': 'pending',
                    }
                }
            }
        ),
        400: openapi.Response(description='잘못된 요청')
    }
)
@api_view(['POST'])
@jwt_auth_optional
@authentication_classes([])
@permission_classes([])
def start_generate_scenario(request):
    """Start a generation job for a scenario.

    Expects JSON { description: str, map_id: int }.
    Returns jobId (uuid) and poll_url for status checks.
    """
    try:
        body = request.data
        description = (body.get('description') or '').strip()
        map_id = body.get('mapId')

        if not description or map_id is None:
            return Response({'status': 400, 'message': 'description and mapId are required'}, status=400)

        job_uuid = str(uuid.uuid4())

        # If user is authenticated, jwt_auth_optional will have set request.user_id.
        uid = None
        if getattr(request, 'user_id', None):
            uid = int(request.user_id)

        # insert into generation_jobs (user_id will be 0 for anonymous)
        uid_val = int(uid) if uid else 0
        with connection.cursor() as cursor:
            insert_sql = (
                "INSERT INTO generation_jobs (job_uuid, user_id, description, map_id, status) "
                "VALUES (%s, %s, %s, %s, %s)"
            )
            cursor.execute(insert_sql, [job_uuid, uid_val, description, map_id, 'pending'])

        # Start background worker immediately (daemon thread) to process this job.
        t = threading.Thread(target=thread_start_generation, args=(job_uuid,), daemon=True)
        t.start()

        data = {
            'jobId': job_uuid, 
            'status': 'pending'
        }
        return Response({'status': 201, 'message': data}, status=201)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return Response({'status': 500, 'message': "500 Internal Server Error"}, status=500)


@swagger_auto_schema(
    method="get",
    operation_summary="시나리오 생성 진행 상태 조회",
    operation_description=(
        "jobId로 생성 작업의 현재 상태와 진행률을 조회합니다.\n"
        "인증은 선택적이며, 로그인되어 있으면 사용자 정보가 job에 기록됩니다."
    ),
    responses={
        200: openapi.Response(
            description="상태 정보",
            examples={
                'application/json': {
                    'status': 200,
                    'message': {
                        'jobId': '<uuid>',
                        'status': 'running',
                        'scenarioId': 12,
                        'mapId': 1
                    }
                }
            }
        ),
        404: openapi.Response(description='작업을 찾을 수 없음')
    }
)
@api_view(['GET'])
@jwt_auth_optional
@authentication_classes([])
@permission_classes([])
def get_generating_state(request, job_uuid):
    """Get generation job status by job_uuid."""
    try:
        # Authentication is optional for generation service; allow anonymous polling.
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, user_id, description, map_id, status, scenario_id FROM generation_jobs WHERE job_uuid = %s", [job_uuid])
            row = cursor.fetchone()
            if not row:
                return Response({'status': 404, 'message': 'job not found'}, status=404)

            (gid, owner_id, description_val, map_id_val, status, scenario_id) = row

            data = {
                'jobId': job_uuid,
                'status': status,
                'scenarioId': int(scenario_id) if scenario_id else None,
                'mapId': map_id_val,
            }

            return Response({'status': 200, 'message': data}, status=200)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return Response({'status': 500, 'message': str(e)}, status=500)
