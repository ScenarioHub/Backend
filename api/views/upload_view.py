from django.db import connection
from rest_framework.decorators import api_view, parser_classes, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from api.decorators import jwt_auth_required
from utils.utils import build_filename, save_scenario_file, save_video_file

@swagger_auto_schema(
    method="post",
    operation_summary="시나리오 업로드",
    operation_description="업로드한 시나리오를 공유합니다.",
    consumes=["multipart/form-data"],
    manual_parameters=[
        openapi.Parameter("Authorization", openapi.IN_HEADER, description="Bearer <JWT 토큰>", 
                          type=openapi.TYPE_STRING),
        openapi.Parameter("title", openapi.IN_FORM, description="Post title",
                          type=openapi.TYPE_STRING, required=True),
        openapi.Parameter("description", openapi.IN_FORM, description="Post description",
                          type=openapi.TYPE_STRING, required=True),
        openapi.Parameter("file", openapi.IN_FORM, description="Post scenario file",
                          type=openapi.TYPE_FILE, required=True),
        openapi.Parameter("tags", openapi.IN_FORM, description="CSV tags (예: 어린이,안전,센서)",
                          type=openapi.TYPE_STRING, required=False),
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

    if (not title or
        not description or
        not uploaded_file):
        return Response(data={'status': '400', 'message': '400 Bad Request'}, status=400)
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

        print(type(tags))
        print(tags)
        
        scenario_path = save_scenario_file(uploaded_file, file_name)
        video_path = save_video_file(scenario_path, file_name)


        scenario_columns = ['owner_id', 'file_url', 'video_url',
                    'file_format', 'file_version', 'file_size',
                    'code_snippet', 'created_at']
        scenario_sql = f"insert into scenarios({','.join(scenario_columns)}) values({','.join(['%s' for _ in range(len(scenario_columns))])})"
        cursor.execute(
            scenario_sql,
            [uid, scenario_path, video_path, 
             'OpenSCENARIO', '1.2', uploaded_file.size,
             'snippet', ts]
        )
        scenario_id = cursor.lastrowid

        post_columns = ['scenario_id', 'uploader_id', 
                       'title', 'template_desc', 'description',
                       'view_count', 'download_count', 'like_count', 'created_at']
        post_sql = f"insert into posts({','.join(post_columns)}) values({','.join(['%s' for _ in range(len(post_columns))])})"
        cursor.execute(
            post_sql,
            [scenario_id, uid,
             title, "", description,
             '0', '0', '0', ts]
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

        status = 201
        message = {
            'postId': post_id,
            'scenarioId': scenario_id,
            'uploaderId': uid,  # 이거로 누가 올렸는지 인증
            'tags': tags
        }
    except Exception as e:
        connection.rollback()
        status = 500
        message = '500 Internal Server Error'

        import traceback
        print(traceback.format_exc())
    finally:
        return Response(
            data={
                'status': status,
                'message': message
            },
            status=status
        )