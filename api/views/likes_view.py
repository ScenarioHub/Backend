from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from api.auth.decorators import jwt_auth_required

@swagger_auto_schema(
    method="post",
    operation_summary="시나리오 좋아요 토글",
    operation_description="로그인한 사용자가 특정 게시물(포스트)의 시나리오에 좋아요를 추가하거나 취소합니다.",
    manual_parameters=[
        openapi.Parameter("postId", openapi.IN_PATH, description="Post ID", type=openapi.TYPE_INTEGER, required=True),
    ],
    responses={
        200: openapi.Response(
            description="좋아요 취소/반환",
            examples={
                'application/json': {
                    'status':200, 
                    'message': {
                        'liked': False, 
                        'likes': 12
                    }
                }
            }
        ),
        201: openapi.Response(
            description="좋아요 추가/반환", 
            examples={
                'application/json': {
                    'status':201, 
                    'message': {
                        'liked': True, 
                        'likes': 13
                    }
                }
            }
        ),
        401: openapi.Response(description="로그인 필요"),
        404: openapi.Response(description="게시물 없음"),
    }
)
@api_view(['POST'])
@jwt_auth_required
@authentication_classes([])
@permission_classes([])
def toggle_like(request, postId):
    """Toggle like for a given post id.

    The endpoint expects a post id (posts.id). The likes table stores likes by scenario_id,
    so we first map the post -> scenario_id and then insert/delete from likes.
    Returns current like status and the updated like_count from posts.
    """

    try:
        uid = int(request.user_id)
        with connection.cursor() as cursor:
            # Find scenario_id for given post id
            cursor.execute("SELECT scenario_id FROM posts WHERE id = %s", [postId])
            row = cursor.fetchone()
            if not row:
                return Response({'status': 404, 'message': '게시물을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

            scenario_id = int(row[0])

            # Check if like already exists
            cursor.execute("SELECT 1 FROM likes WHERE user_id = %s AND scenario_id = %s", [uid, scenario_id])
            exists = cursor.fetchone()

            if exists:
                # remove like
                cursor.execute("DELETE FROM likes WHERE user_id = %s AND scenario_id = %s", [uid, scenario_id])
                # decrement post like_count safely
                cursor.execute("UPDATE posts SET like_count = GREATEST(like_count - 1, 0) WHERE id = %s", [postId])
                # fetch updated count
                cursor.execute("SELECT like_count FROM posts WHERE id = %s", [postId])
                new_count = int(cursor.fetchone()[0])
                connection.commit()
                return Response({'status': 200, 'message': {'liked': False, 'likes': new_count}}, status=status.HTTP_200_OK)
            else:
                # add like
                cursor.execute("INSERT INTO likes (user_id, scenario_id, created_at) VALUES (%s, %s, NOW())", [uid, scenario_id])
                cursor.execute("UPDATE posts SET like_count = like_count + 1 WHERE id = %s", [postId])
                cursor.execute("SELECT like_count FROM posts WHERE id = %s", [postId])
                new_count = int(cursor.fetchone()[0])
                connection.commit()
                return Response({'status': 201, 'message': {'liked': True, 'likes': new_count}}, status=status.HTTP_201_CREATED)

    except Exception:
        connection.rollback()
        
        import traceback
        print(traceback.format_exc())

        return Response({'status': 500, 'message': 'internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
