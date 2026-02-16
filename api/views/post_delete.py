from django.db import connection
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from api.auth.decorators import jwt_auth_required

@swagger_auto_schema(
    method='delete',
    operation_summary="게시물 삭제",
    operation_description="게시물을 삭제합니다.",
    manual_parameters=[
        openapi.Parameter(
            "postId",
            openapi.IN_PATH,
            description="Post ID",
            type=openapi.TYPE_INTEGER,
            required=True,
        )
    ],
    responses={
        200: openapi.Response(
            description="삭제 성공",
            examples={
                'application/json': {
                    'status': 200,
                    'message': "post 1 deleted"
                }
            }
        ),
        403: openapi.Response(
            description="인증 오류",
            examples={
                'application/json': {
                    'status': 403,
                    'message': "403 Forbidden"
                }
            }
        ),
        404: openapi.Response(
            description="게시물 없음",
            examples={
                'application/json': {
                    'status': 404,
                    'message': "404 Not Found"
                }
            }
        ),
    }
)
@api_view(['DELETE'])
@jwt_auth_required
@authentication_classes([])
@permission_classes([])
def delete_post(request, postId):
    try:
        requester_uid = getattr(request, 'user_id', None)
        cursor = connection.cursor()

        str_sql = f"SELECT uploader_id FROM posts WHERE id={postId}"
        cursor.execute(str_sql)
        row = cursor.fetchone()

        if not row:
            return Response(
                data={
                    'status': 404,
                    'message': '404 Not Found'
                },
                status=404
            )
        if requester_uid != int(row[0]):
            return Response(
                data={
                    'status': 403,
                    'message': '403 Forbidden'
                },
                status=403
            )

        str_sql = f"DELETE FROM posts WHERE id={postId}"
        cursor.execute(str_sql)
        row = cursor.fetchone()

        connection.commit()
        connection.close()

        status = 200
        message = f"post {postId} deleted"
        print(row)
    except Exception:
        connection.rollback()
        status = 500
        message = "Internal Server Error"

        import traceback
        print(traceback.format_exc())

    return Response(
        data={
            'status': status,
            'message': message
        },
        status=status
    )