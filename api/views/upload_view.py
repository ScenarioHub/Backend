import os
import jwt
from django.shortcuts import render
from django.db import connection
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes, authentication_classes, permission_classes

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from api.auth.decorators import jwt_auth_required
from utils.utils import build_filename, parse_scenario_snippet, save_scenario_file, save_video_file

@swagger_auto_schema(
    method="post",
    operation_summary="시나리오 업로드",
    operation_description="업로드한 시나리오를 공유합니다.",
    consumes=["multipart/form-data"],
    manual_parameters=[
        openapi.Parameter(
            name="title", 
            in_=openapi.IN_FORM, 
            description="Post title",
            type=openapi.TYPE_STRING, 
            required=True,
        ),
        openapi.Parameter(
            name="description", 
            in_=openapi.IN_FORM, 
            description="Post description",
            type=openapi.TYPE_STRING, 
            required=True
        ),
        openapi.Parameter(
            name="file", 
            in_=openapi.IN_FORM, 
            description="Post scenario file",
            type=openapi.TYPE_FILE, 
            required=True,
            ),
        openapi.Parameter(
            name="mapId", 
            in_=openapi.IN_FORM, 
            description="Map Id",
            type=openapi.TYPE_INTEGER, 
            required=True,
            ),
        openapi.Parameter(
            name="tags", 
            in_=openapi.IN_FORM, 
            description="CSV tags (예: 어린이,안전,센서)",
            type=openapi.TYPE_STRING, 
            required=False,
        ),
    ],
    responses={
        201: openapi.Response(
            description="업로드 성공",
            examples={
                'application/json': {
                    'status': 201,
                    'message': {
                        'postId': '0',
                        'scenarioId': '0',
                        'uploaderId': '0',
                        'tags': ['어린이', '안전', '센서'],
                    }
                }
            }
        ),
        500: openapi.Response(
            description="업로드 실패",
            examples={
                'application/json': {
                    'status': 500,
                    'message': "500 Internal Server Error"
                }
            }
        ),
    },
)

@parser_classes([MultiPartParser, FormParser])
@api_view(['POST'])
@jwt_auth_required  # jwt_auth_required 데코레이터 적용
@authentication_classes([]) # 인증 클래스 비활성화: 안 하면 우리가 사용하는 users테이블이 아닌 장고 기본 auth_user 테이블로 인증 시도
@permission_classes([])     # 권한 클래스 비활성화: 안 하면 우리가 사용하는 users테이블이 아닌 장고 기본 auth_user 테이블로 인증 시도
def upload_post(request):
    title = request.data.get("title", "").strip()
    description = request.data.get("description", "").strip()
    tags = request.data.get("tags", "")
    uploaded_file = request.FILES.get("file", None)
    map_id = request.data.get("mapId", None)

    if (not title or
        not description or
        not uploaded_file or
        not map_id):
        return Response(data={'status': '400', 'message': '필수 항목을 입력하십시오.'}, status=400)
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    else:
        tag_list = []

    uid = int(request.user_id)      #uid 받아오기
    if not uid:
        return Response({'error': '유저 정보를 찾을 수 없습니다.'}, status=401)
    file_name, ts = build_filename(uid, return_ts=True)

    seen = set()
    tag_list = [t for t in tag_list if not (t in seen or seen.add(t))]

    try:
        cursor = connection.cursor()
        
        cursor.execute("select file_url from maps where id=%s", [map_id])
        map_path = cursor.fetchone()
        if map_path is None:
            return Response(
                data={
                    'status': 404,
                    'message': "맵 정보를 찾을 수 없습니다."
                },
                status=404,
            )
        map_path = map_path[0]

        scenario_path = save_scenario_file(uploaded_file, file_name, map_path)
        code_snippet = parse_scenario_snippet(scenario_path)
        video_path = save_video_file(scenario_path, file_name)
        
        # esmini error / ffmpeg error
        if isinstance(video_path, Exception):
            # connection을 직접 닫아주고 즉시 리턴합니다.
            connection.close()
            return Response(
                data={
                    'status': 402, 
                    'message': str(video_path) # "esmini error" 혹은 "ffmpeg error"
                },
                status=402
            )

        # scenario 테이블 저장장
        st_columns = ['owner_id', 'file_url', 'video_url',
                    'file_format', 'file_version', 'file_size',
                    'code_snippet', 'created_at']
        st_sql = f"insert into scenarios({','.join(st_columns)}) values({','.join(['%s' for _ in range(len(st_columns))])})"
        cursor.execute(
            st_sql,
            [uid, scenario_path, video_path, 
            'OpenSCENARIO', '1.2', uploaded_file.size,
            code_snippet, ts]
        )
        scenario_id = cursor.lastrowid

        # posts 테이블 저장
        post_columns = ['scenario_id', 'uploader_id', 
                    'title', 'template_desc', 'description',
                    'view_count', 'download_count', 'like_count', 'created_at']
        post_sql = f"insert into posts({','.join(post_columns)}) values({','.join(['%s' for _ in range(len(post_columns))])})"
        cursor.execute(
            post_sql,
            [scenario_id, uid,
            title, "", description,
            0, 0, 0, ts]
        )
        post_id = cursor.lastrowid

        # 3) tags + scenario_tags
        if tag_list:
            # If tags.created_at has DEFAULT CURRENT_TIMESTAMP you can omit it,
            # but since you asked to reflect the column explicitly, we insert it.
            values_sql = ",".join(["(%s, %s)"] * len(tag_list))
            params = []
            for name in tag_list:
                params.extend([name, ts])

            insert_tags_sql = (
                f"INSERT INTO tags(name, created_at) VALUES {values_sql} "
                f"ON DUPLICATE KEY UPDATE name = name"
            )
            cursor.execute(insert_tags_sql, params)

            in_placeholders = ",".join(["%s"] * len(tag_list))
            insert_map_sql = (
                "INSERT IGNORE INTO scenario_tags (scenario_id, tag_id) "
                "SELECT %s AS scenario_id, t.id AS tag_id "
                f"FROM tags t WHERE t.name IN ({in_placeholders})"
            )
            cursor.execute(insert_map_sql, [scenario_id, *tag_list])

        connection.close()
        return Response(
            data={
                'status': 201,
                'message': {
                    'postId': post_id,
                    'scenarioId': scenario_id,
                    'uploaderId': uid,
                    'tags': tags
                }
            },
            status=201
        )
        
    except Exception as e:
        connection.rollback()
        
        import traceback
        print(traceback.format_exc())
        
        # 에러 시 리턴
        return Response(
            data={
                'status': 500,
                'message': '500 Internal Server Error'
            },
            status=500
        )