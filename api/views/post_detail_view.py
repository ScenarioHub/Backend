import os
from django.shortcuts import render
from django.db import connection
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from api.auth.decorators import jwt_auth_optional

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
                        'id': 0,
                        'title': '어린이 주행 시나리오',
                        'created_at': '2025-12-28 16:01:45',
                        'description': '어린이 보호구역에서 다양한 돌발 상황(도로 횡단, 차 사이에서 등장 등)을 포함한 시나리오입니다.',
                        'code': '<OpenSCENARIO>...</OpenSCENARIO>',
                        'tags': ['어린이', '안전', '센서'],
                        'stats': { 'downloads': 0, 'views': 0, 'likes': 0 },
                        'isLiked': False,
                        'isOwner': False,
                        'file': { 'format': 'OpenSCENARIO', 'version': '1.2', 'size': 100},
                        'uploader': {
                            'name': 'user',
                            'uploaderId': 1,
                            'email': 'email@email.com',
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
@jwt_auth_optional
@authentication_classes([])
@permission_classes([])
def scenario_detail(request, id):
    try:
        cursor = connection.cursor()
        # 파일 경로 확인: url에서 xosc 가져와야 하니까
        cursor.execute("SELECT file_url FROM scenarios WHERE id = %s", [id])
        row = cursor.fetchone()
        if not row:
            return Response({'status': 404, 'message': 'Scenario Not Found'}, status=404)
        file_path = row[0]
        if file_path:
            # 윈도우/리눅스 환경에 맞춰 경로 구분자를 자동 교정합니다.
            file_path = os.path.normpath(file_path)

        code_snippet = ""

        # 파일 파싱 (상위 100줄)
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = [next(f) for _ in range(50)]
                    code_snippet = "".join(lines)
            except (StopIteration, Exception):  # 50줄 미만이면 전체
                with open(file_path, 'r', encoding='utf-8') as f:
                    code_snippet = f.read()
        
        # posts 테이블 view count 증가
        update_view_count_sql = "UPDATE posts SET view_count = view_count + 1 WHERE id = %s"
        cursor.execute(update_view_count_sql, [id])
        
        update_snippet_sql = "UPDATE scenarios SET code_snippet = %s WHERE id = %s"
        cursor.execute(update_snippet_sql, [code_snippet, id])
        connection.commit()

        columns = ['id', 'title', 'description', 'createdAt', 'code',   # 여기선 불러오는거니까 createdAt
                   'file_format', 'file_version', 'file_size',
                   'stats_downloads', 'stats_views', 'stats_likes',
                   'uploader_name', 'uploader_initials', 'uploader_email', 'uploader_total_scenarios',
                   'tags']
        sql_query = f"SELECT {','.join(columns)} FROM view_scenario_details WHERE id = %s"     # 수정, 기존 방식은 url에 id를 직접 넣음, 지금은 파라미터로 처리
        cursor.execute(sql_query, [id]) 
        view = cursor.fetchone()

        if not view:
            status = 404
            return Response(
                {'status': 404,
                 'message': 'view가 없습니다.'}, 
                 status=404)

        view = {col: val for col, val in zip(columns, view)}
        
        if view['tags']:
            view['tags'] = [tag.strip() for tag in view['tags'].split(',')]
        else:
            view['tags'] = []
        
        sql_query = f"select id from users where email='{view['uploader_email']}'"
        cursor.execute(sql_query)
        uid = int(cursor.fetchone()[0])

        # determine if the requesting user bookmarked this scenario
        requester_uid = getattr(request, 'user_id', None)

        liked = False
        owner = False
        # find scenario_id for this post (posts.id == id)
        cursor.execute("SELECT scenario_id FROM posts WHERE id = %s", [id])
        sc_row = cursor.fetchone()
        scenario_id = int(sc_row[0]) if sc_row else None

        if requester_uid and scenario_id:
            cursor.execute("SELECT 1 FROM likes WHERE user_id = %s AND scenario_id = %s", [requester_uid, scenario_id])
            if cursor.fetchone():
                liked = True
        if uid == requester_uid:
            owner = True

        connection.commit()
        #connection.close()
        
        message = {
            'id': view['id'],
            'title': view['title'],
            'created_at': view['createdAt'],
            'description': view['description'],
            'code': view['code'],
            'tags': view['tags'],
            'stats': { 'downloads': view['stats_downloads'], 
                      'views': view['stats_views'], 
                      'likes': view['stats_likes'] },
            'isLiked': False,
            'file': { 'format': view['file_format'], 
                     'version': view['file_version'], 
                     'size': view['file_size']},
            'uploader': {
                'name': view['uploader_name'],
                'uploaderId': uid, 
                'email': view['uploader_email'],
                'totalScenarios': view['uploader_total_scenarios']
            }
        }
        status = 200

    except Exception as e:
        if connection:
            connection.rollback()
        status = 404
        message = '404 Not Found'
    finally:
        if cursor:
            cursor.close()

        return Response(
            data={'status': status, 
                  'message': message},
            status=status
        )
