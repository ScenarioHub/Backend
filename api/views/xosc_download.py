import os

from django.db import connection
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

@swagger_auto_schema(
    method="get",
    operation_summary="시나리오 파일 다운로드",
    operation_description="시나리오 파일을 다운로드 합니다.",
    responses={
        200: openapi.Response(
            description="다운로드 성공",
            examples={
                'application/octet-stream': {
                    "status": 200,
                    "data": "download URL"
                },
            }
        ),
        404: openapi.Response(
            description="파일을 찾을 수 없음",
            examples={
                'application/json': {
                    'status': 404,
                    'message': "404 Not Found"
                }
            }
        ),
        500: openapi.Response(
            description="서버 에러",
            examples={
                'application/json': {
                    'status': 500,
                    'message': "500 Internal Server Error"
                }
            }
        ),
    },
)
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def download_file(request, scenarioId):
    with connection.cursor() as cursor:

        # DB에서 리눅스 절대 경로 조회
        cursor.execute("SELECT file_url FROM scenarios WHERE id = %s", [scenarioId])
        row = cursor.fetchone()
        if not row:
            status = 404
            return Response(
                data={
                    'status': status,
                    'message': "파일 정보가 DB에 없습니다."
                },
                status=status
            )
        linux_path = row[0]

        if not os.path.exists(linux_path):
                # 메시지를 "file_url이 잘못되었습니다"로 하셔도 무방합니다.
                return Response({'status': 404, 'message': "file_url이 잘못되었습니다. (파일 미존재)"}, status=404)

        # 다운로드 횟수(download_count) 1 증가 업데이트
        cursor.execute("UPDATE posts SET download_count = download_count + 1 WHERE id = %s", [scenarioId])
        connection.commit() # Raw SQL이므로 확정(commit) 필요
        
    # 3. 외부 서버에 요청하여 파일을 스트리밍으로 전달
    try:
        f = open(linux_path, "rb")

        filename = os.path.basename(linux_path)
        response = StreamingHttpResponse(f, content_type="application/octet-stream")
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except FileNotFoundError:
        status = 404
        return Response(
                data={
                    'status': status,
                    'message': "500 Internal Server Error"
                },
                status=status
            )
    except Exception:
        import traceback
        print(traceback.format_exc())
                
        return Response(
                data={
                    'status': status,
                    'message': "500 Internal Server Error"
                },
                status=status
            )
    
@swagger_auto_schema(
    method="get",
    operation_summary="시나리오 파일 다운로드 (공유 페이지)",
    operation_description="시나리오 파일을 다운로드 합니다.",
    responses={
        200: openapi.Response(
            description="다운로드 성공",
            examples={
                'application/octet-stream': {
                    "status": 200,
                    "data": "download URL"
                },
            }
        ),
        404: openapi.Response(
            description="파일을 찾을 수 없음",
            examples={
                'application/json': {
                    'status': 404,
                    'message': "404 Not Found"
                }
            }
        ),
        500: openapi.Response(
            description="서버 에러",
            examples={
                'application/json': {
                    'status': 500,
                    'message': "500 Internal Server Error"
                }
            }
        ),
    },
)
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def download_file_board(request, postId):
    try:
        with connection.cursor() as cursor:
            cursor.execute("select scenario_id from posts where id=%s", [postId])
            scenario_id = cursor.fetchone()
            if scenario_id is None:
                status = 404
                return Response(
                    data = {
                        'message': '시나리오를 찾을 수 없음',
                        'status': status
                    }, 
                    status=status
                )
            scenario_id = scenario_id[0]
        return redirect(f"/api/scenarios/{scenario_id}/download/")
    except Exception:
        status = 500

        import traceback
        print(traceback.format_exc())

        return Response(
            data={
                'status': status,
                'message': "500 Internal Server Error",
                 },
            status=status
        )