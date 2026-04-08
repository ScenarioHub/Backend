import math

from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from api.auth.decorators import jwt_auth_optional

@swagger_auto_schema(
    method="get",
    operation_summary="시나리오 목록 조회",
    operation_description="시나리오 목록을 조회합니다.",
    manual_parameters=[
        openapi.Parameter(
            name='page', 
            in_=openapi.IN_QUERY, 
            description="조회할 페이지 번호 (기본값: 1)", 
            type=openapi.TYPE_INTEGER, 
            default=1
        ),
        openapi.Parameter(
            name='sort', 
            in_=openapi.IN_QUERY, 
            description="정렬 기준: popular(인기순), latest(최신순), oldest(오래된순)", 
            type=openapi.TYPE_STRING, 
            default='latest'
        ),
        openapi.Parameter(
            name='isLiked', 
            in_=openapi.IN_QUERY,
            description='1 또는 true 로 설정하면 내가 좋아요한 게시물만 반환 (로그인 필요)',
            type=openapi.TYPE_STRING,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="조회 성공",
            examples={
                'application/json': {
                    "status": 200,
                    "message": {
                        "posts": [
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
                                "uploader": {
                                    "name": "name",
                                    "uploaderId": 1
                                },
                                "tags": ["55", "555"],
                                "isLiked": False
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
                                "uploader": {
                                    "name": "name",
                                    "uploaderId": 1
                                },
                                "tags": [],
                                "isLiked": False
                            },
                        ],
                        "totalPages": 3,
                        "currentPage": 1,
                        "totalCount": 32,
                        "sort": "latest"
                    }
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
@jwt_auth_optional
@authentication_classes([])
@permission_classes([])
def post_list(request):
    """함수 기반의 Raw SQL 게시글 목록 조회

    Query params:
      - page (int, default=1)               # 페이지 수
      - page_size (int, default=12)         # 페이지에 보여줄 게시글의 수
      - sort (String, default='latest')     # 게시글 정렬 기준
    """
    try:
        # pagination
        try:
            page = int(request.query_params.get('page', 1))
            if page < 1:
                page = 1
        except Exception:
            page = 1

        page_size = 12

        # 정렬 파라미터 수신 
        sort_by = request.query_params.get('sort', 'latest')

        # 정렬 조건에 따른 SQL 구문 결정
        if sort_by == 'popular':
            order_query = "ORDER BY p.like_count DESC NULLS LAST" # pgsql, NULL이 맨 위로 올라올 수 있어서 수정
        elif sort_by == 'oldest':
            order_query = "ORDER BY p.created_at ASC"
        else:                                          # 기본값은 최신순(latest)
            order_query = "ORDER BY p.created_at DESC"

        offset = (page - 1) * page_size

        # bookmarked 필터 여부 확인
        liked_flag = str(request.query_params.get('isLiked', '')).lower() in ['1', 'true', 'yes']

        # 전체 게시글 개수 조회 (페이지 계산을 위한) - 필터가 걸려있다면 likes 조인을 포함
        if liked_flag:
            # 필터가 걸려있으면 로그인 필요
            if not getattr(request, 'user_id', None):
                return Response({'status': 401, 'message': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM posts p JOIN likes l ON p.scenario_id = l.scenario_id WHERE l.user_id = %s", [request.user_id])
                total_count = cursor.fetchone()[0]
        else:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM posts")
                total_count = cursor.fetchone()[0]
        # 전체 페이지 수 계산
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

        # 게시글 조회 SQL: bookmarked 필터가 있으면 likes 조인 및 사용자 조건 추가
        if liked_flag:
            sql_query = f'''
                SELECT p.id, p.title, p.description, p.created_at, p.view_count, p.like_count, p.download_count,
                       u.name as uploader_name, u.initials as uploader_initials, u.id as uid
                FROM posts p
                JOIN users u ON p.uploader_id = u.id
                JOIN likes l ON p.scenario_id = l.scenario_id AND l.user_id = %s
                {order_query}
                LIMIT %s OFFSET %s
            '''
            query_params = [request.user_id, page_size, offset]
        else:
            sql_query = f'''
                SELECT p.id, p.title, p.description, p.created_at, p.view_count, p.like_count, p.download_count,
                       u.name as uploader_name, u.initials as uploader_initials, u.id as uid
                FROM posts p
                JOIN users u ON p.uploader_id = u.id
                {order_query}
                LIMIT %s OFFSET %s
            '''
            query_params = [page_size, offset]

        with connection.cursor() as cursor:
            cursor.execute(sql_query, query_params)
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
                'uploader': {
                    'name': r[7],
                    'uploaderId': r[9]
                },
                'tags': '',
                'isLiked': False,
            })

        # optional: user id set by jwt_optional decorator (or None)
        uid = getattr(request, 'user_id', None)

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

        # If user is known, also fetch which of these posts are liked by the user
        if uid and post_ids:
            # If bookmarked_flag is set, all returned posts are liked by the user
            if liked_flag:
                for p in posts:
                    p['isLiked'] = True
            else:
                placeholder = ','.join(['%s'] * len(post_ids))
                like_sql = f"SELECT p.id FROM posts p JOIN likes l ON p.scenario_id = l.scenario_id WHERE l.user_id = %s AND p.id IN ({placeholder})"
                with connection.cursor() as cursor:
                    cursor.execute(like_sql, [uid, *post_ids])
                    liked_rows = cursor.fetchall()
                liked_post_ids = {r[0] for r in liked_rows}
                for p in posts:
                    if p['id'] in liked_post_ids:
                        p['isLiked'] = True

        return Response({
            "status": 200, 
            "message": {
                "posts": posts,
                "totalPages": total_pages,  # 전체 페이지 수 (프론트엔드의 요청사항: 개시물 최대 페이지 개수 → 전체 페이지 수)
                "currentPage": page,        # 현재 페이지
                "totalCount": total_count,  # 전체 게시글 수
                "sort": sort_by             # 현재 적용된 정렬 기준을 프론트엔드에 전달
                }
            },
            status=status.HTTP_200_OK)

    except Exception:
        import traceback
        print(traceback.format_exc())
        
        return Response({"status": 500, "message": "internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)