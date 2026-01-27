from django.shortcuts import render
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

@swagger_auto_schema(
    method="get",
    operation_summary="시나리오 목록 조회",
    operation_description="시나리오 목록을 조회합니다.",
    responses={
        200: openapi.Response(
            description="조회 성공",
            examples={
                'application/json': {
                    "status": 200,
                    "message": [
                        {
                            "id": 28,
                            "title": "4",
                            "description": "4",
                            "createdAt": "2026-01-04 21:20:07",
                            "stats": {
                                "downloads": 0,
                                "views": 0,
                                "likes": 0,
                            },
                            "uploader_info": {
                                "uploader_name": "name",
                                "uploader_id": 1
                            },
                            "tags": ["55", "555"],
                            "isBookmarked": False
                        },
                        {
                            "id": 27,
                            "title": "4",
                            "description": "4",
                            "createdAt": "2026-01-04 21:19:10",
                            "stats": {
                                "downloads": 0,
                                "views": 0,
                                "likes": 0,
                            },
                            "uploader_info": {
                                "uploader_name": "name",
                                "uploader_id": 1
                            },
                            "tags": [],
                            "isBookmarked": False
                        },
                    ]
                },
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
def post_list(request):
    """함수 기반의 Raw SQL 게시글 목록 조회

    Query params:
      - page (int, default=1)
      - page_size (int, default=12)
    """
    try:
        # pagination
        try:
            page = int(request.query_params.get('page', 1))
            if page < 1:
                page = 1
        except Exception:
            page = 1
        try:
            page_size = int(request.query_params.get('page_size', 12))
            if page_size < 1:
                page_size = 12
        except Exception:
            page_size = 12

        offset = (page - 1) * page_size

        sql = '''
            SELECT p.id, p.title, p.description, p.created_at, p.view_count, p.like_count, p.download_count,
                   u.name as uploader_name, u.initials as uploader_initials, u.id as uid
            FROM posts p
            JOIN users u ON p.uploader_id = u.id
            ORDER BY p.created_at DESC
            LIMIT %s OFFSET %s
        '''

        with connection.cursor() as cursor:
            cursor.execute(sql, [page_size, offset])
            rows = cursor.fetchall()

        posts = []
        post_ids = []
        for r in rows:
            pid = r[0]
            post_ids.append(pid)
            posts.append({
                'id': pid,
                'title': r[1],
                'description': r[2],
                'createdAt': r[3].strftime("%Y-%m-%d %H:%M:%S") if r[3] else None,
                'stats': {
                    'downloads': r[6],
                    'views': r[4],
                    'likes': r[5],
                },
                'uploader_info': {
                    'uploader_name': r[7],
                    'uploader_id': r[9]
                },
                'tags': '',
                'isBookmarked': False,
            })

        if post_ids:
            # posts -> scenarios (posts.scenario_id) -> scenario_tags -> tags
            placeholder = ','.join(['%s'] * len(post_ids))
            tag_sql = f"SELECT p.id, t.name FROM posts p JOIN scenario_tags st ON p.scenario_id = st.scenario_id JOIN tags t ON st.tag_id = t.id WHERE p.id IN ({placeholder})"
            with connection.cursor() as cursor:
                cursor.execute(tag_sql, post_ids)
                tag_rows = cursor.fetchall()

            tags_map = {}
            for pr_id, tname in tag_rows:
                tags_map.setdefault(pr_id, []).append(tname)

            for p in posts:
                tlist = tags_map.get(p['id'], [])[:5]
                p['tags'] = tlist

        return Response({"status": 200, "message": posts}, status=status.HTTP_200_OK)

    except Exception:
        import traceback
        print(traceback.format_exc())
        return Response({"status": 500, "message": "internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)