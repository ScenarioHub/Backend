from django.shortcuts import render
from django.db import connection
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from .utils import build_filename, save_scenario_file, save_video_file

@swagger_auto_schema(
    method="get",
    operation_summary="시나리오 상세 조회",
    operation_description="시나리오 ID로 시나리오 상세 정보를 조회합니다.",
    manual_parameters=[
        openapi.Parameter(
            "id",
            openapi.IN_PATH,
            description="Scenario ID",
            type=openapi.TYPE_INTEGER,
            required=True,
        )
    ],
    responses={
        200: openapi.Response(
            description="조회 성공",
            examples={
                'application/json': {
                    'status': 200,
                    'message': {
                        'id': '0',
                        'title': '어린이 주행 시나리오',
                        'createdAt': '2025-12-28 16:01:45',
                        'description': '어린이 보호구역에서 다양한 돌발 상황(도로 횡단, 차 사이에서 등장 등)을 포함한 시나리오입니다.',
                        'code': '<OpenSCENARIO>...</OpenSCENARIO>',
                        'tags': ['어린이', '안전', '센서'],
                        'stats': { 'downloads': 0, 'views': 0, 'likes': 0 },
                        'isBookmarked': 'FALSE',
                        'file': { 'format': 'OpenSCENARIO', 'version': '1.2', 'size': '100 KB'},
                        'uploader': {
                            'name': 'user',
                            'email': 'email@email.com',
                            'initials': 'US',
                            'totalScenarios': 12
                        }
                    }
                }
            }
        ),
        404: openapi.Response(
            description="시나리오 없음",
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
def scenario_detail(request, id):
    try:
        cursor = connection.cursor()
        columns = ['id', 'title', 'description', 'createdAt', 'code',
                   'file_format', 'file_version', 'file_size',
                   'stats_downloads', 'stats_views', 'stats_likes',
                   'uploader_name', 'uploader_initials', 'uploader_email', 'uploader_total_scenarios',
                   'tags']
        strSql = f"select {','.join(columns)} from view_scenario_details where id={id}"
        cursor.execute(strSql)
        view = cursor.fetchone()
        view = {col: val for col, val in zip(columns, view)}
        view['tags'] =[tag.strip() for tag in view['tags'].split(',')]
        
        connection.commit()
        connection.close()
        
        message = {
            'id': view['id'],
            'title': view['title'],
            'createdAt': view['createdAt'],
            'description': view['description'],
            'code': view['code'],
            'tags': view['tags'],
            'stats': { 'downloads': view['stats_downloads'], 'views': view['stats_views'], 'likes': view['stats_likes'] },
            'isBookmarked': 'FALSE',
            'file': { 'format': view['file_format'], 'version': view['file_version'], 'size': view['file_size']},
            'uploader': {
                'name': view['uploader_name'],
                'initials': view['uploader_initials'],
                'email': view['uploader_email'],
                'totalScenarios': view['uploader_total_scenarios']
            }
        }
    except Exception as e:
        connection.rollback()
        status = 404
        message = '404 Not Found'
    else:
        status = 200
    finally:
        return Response(
            data={
                'status': status,
                'message': message
            },
            status=status
        )

@swagger_auto_schema(
    method="post",
    operation_summary="시나리오 업로드",
    operation_description="업로드한 시나리오를 공유합니다.",
    consumes=["multipart/form-data"],
    manual_parameters=[
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

    uid = 1      #dummy
    file_name, ts = build_filename(uid, return_ts=True)

    seen = set()
    tag_list = [t for t in tag_list if not (t in seen or seen.add(t))]

    try:
        cursor = connection.cursor()

        print(type(tags))
        print(tags)
        
        scenario_path = save_scenario_file(uploaded_file, file_name)
        video_path = save_video_file(scenario_path, file_name)


        st_columns = ['owner_id', 'file_url', 'video_url',
                    'file_format', 'file_version', 'file_size',
                    'code_snippet', 'created_at']
        st_sql = f"insert into scenarios({','.join(st_columns)}) values({','.join(['%s' for _ in range(len(st_columns))])})"
        cursor.execute(
            st_sql,
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
            'uploaderId': uid,
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