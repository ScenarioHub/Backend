import os
import time
from django.db import connection, transaction
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
        openapi.Parameter('jobId', openapi.IN_PATH, type=openapi.TYPE_STRING, required=True, description="작업 UUID"),
    ],
    responses={
        200: openapi.Response(
            description="조회 성공", 
            examples={
                'application/json': {
                    "status": 200,
                    "message": {
                        "description": "시나리오 설명",
                        "mapId": 1,
                        "scenarioId": 1,
                        "filePath": "C:/Users/user/Desktop/scenario/20260127_220824_0.xosc",
                        "videoPath": "C:/Users/user/Desktop/scenario/20260127_220824_0.mp4"
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
def get_generated_data(request, jobId):
    uid = int(request.user_id)

    try:
        with transaction.atomic():
            cursor = connection.cursor()

            # 1. jobId를 통해 시나리오 경로와 동영상 경로를 함께 조회
            query_check = """
                SELECT g.user_id, g.scenario_id, s.file_url, s.video_url 
                FROM generation_jobs g
                JOIN scenarios s ON g.scenario_id = s.id
                WHERE g.job_uuid = %s
            """
            cursor.execute(query_check, [jobId])
            job_info = cursor.fetchone()
            
            if not job_info:
                return Response({'status': 404, 'message': '존재하지 않는 작업입니다.'}, status=404)
        
        current_owner, scenario_id, old_file_path, old_video_path = job_info
        
        # 2. 비로그인(0) 상태라면 소유권 이전 및 파일명 변경 진행
        if current_owner == 0:
            new_file_path = old_file_path
            new_video_path = old_video_path
            
            # [A] 시나리오 파일명 변경 (_0.xosc -> _uid.xosc)
            if old_file_path and old_file_path.endswith('_0.xosc'):
                new_file_path = old_file_path.replace('_0.xosc', f'_{uid}.xosc')
                try:
                    if os.path.exists(old_file_path):
                        os.rename(old_file_path, new_file_path)
                except OSError as e:
                    print(f"시나리오 파일명 변경 실패: {e}")

            # [B] 동영상 파일명 변경 (_0.mp4 -> _uid.mp4)
            if old_video_path and old_video_path.endswith('_0.mp4'):
                new_video_path = old_video_path.replace('_0.mp4', f'_{uid}.mp4')
                try:
                    if os.path.exists(old_video_path):
                        os.rename(old_video_path, new_video_path)
                except OSError as e:
                    print(f"동영상 파일명 변경 실패: {e}")

        # 3. DB 업데이트: 두 테이블의 모든 경로 정보 동기화
            cursor.execute("UPDATE generation_jobs SET user_id = %s WHERE job_uuid = %s", [uid, jobId])
            cursor.execute("""
                UPDATE scenarios 
                SET owner_id = %s, file_url = %s, video_url = %s 
                WHERE id = %s
            """, [uid, new_file_path, new_video_path, scenario_id])
            
            final_file_path = new_file_path
            final_video_path = new_video_path
        
        elif current_owner != uid:
            return Response({'status': 403, 'message': '권한이 없습니다.'}, status=403)
        else:
            final_file_path = old_file_path
            final_video_path = old_video_path

            # 4. 최종 데이터 조회
            cursor.execute("SELECT description, map_id FROM generation_jobs WHERE job_uuid = %s", [jobId])
            description, map_id = cursor.fetchone()

        return Response({
            'status': 200,
            'message': {
                'description': description, 
                'mapId': map_id, 
                'scenarioId': scenario_id,
                'filePath': final_file_path,
                'videoPath': final_video_path
            }
        }, status=200)
    except Exception as e:
        import traceback
        print(traceback.format_exc())

        return Response(
            data={
                'status': 500,
                'message': "500 Internal Server Error"
            },
            status=500
        )
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
        openapi.Parameter(
            name="jobId", 
            in_=openapi.IN_PATH, 
            description="작업 UUID",
            type=openapi.TYPE_STRING, 
            required=True, 
        ),
        openapi.Parameter(
            name="title", 
            in_=openapi.IN_FORM, 
            description="게시글 제목",
            type=openapi.TYPE_STRING, 
            required=True, 
        ),
        openapi.Parameter(
            name="tags", 
            in_=openapi.IN_FORM, 
            type=openapi.TYPE_STRING, 
            description="쉼표 구분 태그",
            required=False, 
        ),
    ],
    responses={
        200: openapi.Response(
            description="생성 후 업로드 성공", 
            examples={
                'application/json': {
                    "status": 201,
                    "message": {
                        "postId": 0,
                        "scenarioId": 0,
                        "mapId": 5,
                        "description": "0212_0248",
                        "filePath": "/home/scenariohub/ScenarioHub/data/xosc/cut-in.xosc"
                    }
              }
            }
        ),
            404: openapi.Response(
                description="데이터 없음",
                examples={
                    'application/json': {
                        'status': 403, 
                        'message': '권한이 없거나 유효하지 않은 생성 데이터입니다.'
                        }
                }
            ),
    }
)
@parser_classes([MultiPartParser, FormParser])
@api_view(['POST'])
@jwt_auth_required
@authentication_classes([])
@permission_classes([])
def upload_from_generation(request, jobId):
    title = request.data.get("title", "").strip()
    tags = request.data.get("tags", "")
    uid = int(request.user_id)

    try:
        cursor = connection.cursor()

        # 소유권 업데이트 로직 (GET과 동일하게 적용하여 안전장치 마련)
        cursor.execute("UPDATE generation_jobs SET user_id = %s WHERE job_uuid = %s AND user_id = 0", [uid, jobId])

        # 1. job_uuid를 통해 상세 정보(description, map_id)와 시나리오 파일 경로(file_url)를 함께 조회
        cursor.execute("""
            SELECT g.scenario_id, g.description, g.map_id, s.file_url 
            FROM generation_jobs g
            JOIN scenarios s ON g.scenario_id = s.id
            WHERE g.job_uuid = %s AND g.user_id = %s
        """, [jobId, uid])
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