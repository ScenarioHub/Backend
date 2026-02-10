import os
import time
from django.db import connection
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes, authentication_classes, permission_classes
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from api.auth.decorators import jwt_auth_required

# --- [GET] 생성 데이터 조회 ---
@swagger_auto_schema(
    method="get",
    operation_summary="생성 시나리오 데이터 조회",
    operation_description="job_uuid를 통해 scenario_id, map_id, description을 가져옵니다.",
    # 조회에 필요한 uuid만 남기고 나머지는 제거하세요.
    manual_parameters=[
        openapi.Parameter('job_uuid', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="작업 UUID"),
    ],
    responses={
        200: openapi.Response(
            description="조회 성공", 
            examples={
                'application/json': {
                    "status": 200,
                    "data": {
                        "description": "시나리오 설명",
                        "mapId": 1,
                        "scenarioId": 1,
                        "filePath": "C:/Users/user/Desktop/scenario/20260127_220824_2.xosc"
                    }
              }
            }
        ),
               404: openapi.Response(
                   description="데이터 없음",
                   examples={
                       'application/json': {
                           "status": 404,
                           "message": "데이터 없음 (UID: 1, UUID: abcd-efgh-ijkl-mnop)"
                       }
                   }
                ),
    }
)
@api_view(['GET'])
@jwt_auth_required
@authentication_classes([])
@permission_classes([])
def get_scenario_data(request):
    job_uuid = request.GET.get("job_uuid")
    uid = int(request.user_id)

    try:
        cursor = connection.cursor()
        # generation_jobs와 scenarios를 조인하여 상세 정보 추출
        query = """
            SELECT g.description, g.map_id, g.scenario_id, s.file_url 
            FROM generation_jobs g
            JOIN scenarios s ON g.scenario_id = s.id
            WHERE g.job_uuid = %s AND g.user_id = %s
        """
        cursor.execute(query, [job_uuid, uid])
        row = cursor.fetchone()
        
        if not row:
            return Response({ 'status': 404, 
                             'message': f'데이터 없음 (UID: {uid}, UUID: {job_uuid})' }, 
                             status=404)

        return Response({
            'status': 200,
            'data': {
                'description': row[0], 
                'mapId': row[1], 
                'scenarioId': row[2],
                'filePath': (row[3])
            }
        }, status=200)
    finally:
        connection.close()

# --- [POST] 생성 시나리오 기반 업로드 ---
@swagger_auto_schema(
    method="post",
    operation_summary="생성 시나리오 공유하기",
    operation_description="생성된 결과물(job_uuid)을 기반으로 게시글을 생성합니다.",
    consumes=["multipart/form-data"],
    # request_body를 빈 오브젝트로 명시하여 자동 생성을 막습니다.
    # request_body=openapi.Schema(type=openapi.TYPE_OBJECT), 
    manual_parameters=[
        openapi.Parameter("jobId", openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, description="작업 UUID"),
        openapi.Parameter("title", openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, description="게시글 제목"),
        openapi.Parameter("tags", openapi.IN_FORM, type=openapi.TYPE_STRING, required=False, description="쉼표 구분 태그"),
    ],
    responses={"201": "공유 성공"}
)


@parser_classes([MultiPartParser, FormParser])
@api_view(['POST'])
@jwt_auth_required
@authentication_classes([])
@permission_classes([])
def upload_from_generation(request):
    job_uuid = request.data.get("jobId")
    title = request.data.get("title", "").strip()
    tags = request.data.get("tags", "")
    uid = int(request.user_id)

    try:
        cursor = connection.cursor()
        # 1. job_uuid를 통해 상세 정보(description, map_id)와 시나리오 파일 경로(file_url)를 함께 조회
        cursor.execute("""
            SELECT g.scenario_id, g.description, g.map_id, s.file_url 
            FROM generation_jobs g
            JOIN scenarios s ON g.scenario_id = s.id
            WHERE g.job_uuid = %s AND g.user_id = %s
        """, [job_uuid, uid])
        job_data = cursor.fetchone()
        
        if not job_data:
            return Response({'status': 403, 'message': '권한이 없거나 유효하지 않은 생성 데이터입니다.'}, status=403)
        
        scenario_id, description, map_id, file_url = job_data

        # 2. posts 테이블에 INSERT
        post_columns = ['scenario_id', 'uploader_id', 'title', 'description', 'created_at']
        post_sql = f"""
            INSERT INTO posts (scenario_id, uploader_id, title, description, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """
        post_values = [scenario_id, uid, title, description]
        # print(f"\n--- API 데이터 입력 확인 ---")
        # print(f"조회된 Scenario ID: {scenario_id}")
        # print(f"자동 입력될 Description: {description}")
        # print(f"연결된 Map ID: {map_id}")
        # print(f"---------------------------\n")

        #post_sql = f"INSERT INTO posts ({', '.join(post_columns)}) VALUES ({', '.join(['%s']*len(post_columns))})"
        
        cursor.execute(post_sql, post_values)
        post_id = cursor.lastrowid

        # 3. 태그 처리 로직 (기존과 동일)
        if tags:
            tag_list = list(set([t.strip() for t in tags.split(",") if t.strip()]))
            if tag_list:
                # %s 하나를 NOW()로 교체하여 DB 시간을 직접 입력합니다.
                values_sql = ",".join(["(%s, NOW())"] * len(tag_list)) 
                params = []
                for name in tag_list: 
                    params.append(name) # 이제 name만 넣으면 됩니다.

                insert_tags_sql = (
                    f"INSERT INTO tags(name, created_at) VALUES {values_sql} "
                    f"ON DUPLICATE KEY UPDATE name = name"
                )
                cursor.execute(insert_tags_sql, params)

        connection.close()
        return Response({
            'status': 201, 
            'message': {
                'postId': post_id,
                'scenarioId': scenario_id,
                'mapId': map_id,
                'description': description,
                'filePath': file_url
            }
        }, status=201)
    
    except Exception as e:
        connection.rollback()
        return Response({'status': 500, 
                         'message': str(e)}, 
                         status=500)