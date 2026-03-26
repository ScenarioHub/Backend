from django.conf import settings
from django.http import FileResponse
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


@swagger_auto_schema(
    method="GET",
    operation_summary="리소스 파일 제공",
    operation_description="서버의 모델 및 맵 GLB 파일을 클라이언트로 제공합니다.",
    responses={
        200: openapi.Response(description="파일 스트림 (application/octet-stream)"),
        400: openapi.Response(description="잘못된 요청 (유효하지 않은 타입 또는 경로)"),
        404: openapi.Response(description="파일을 찾을 수 없음")
    }
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def serve_content_file(request, file_type, filename):
    # 파일 타입에 따른 디렉토리 매핑
    if file_type == 'models-glb':
        directory = settings.DATA_ROOT / 'models_glb'
    elif file_type == 'xodr-glb':
        directory = settings.DATA_ROOT / 'xodr_glb'
    else:
        return Response({"status": 400, "message": "유효하지 않은 파일 타입입니다."}, status=400)

    # 보안 검사: Directory Traversal 방지
    try:
        # resolve()는 심볼릭 링크를 풀고 절대 경로를 정규화합니다.
        resolved_dir = directory.resolve()
        file_path = (directory / filename).resolve()
    except Exception:
        return Response({"status": 400, "message": "잘못된 파일 경로입니다."}, status=400)

    # 요청된 파일 경로가 지정된 디렉토리 하위에 있는지 부모-자식 관계 확인
    try:
        # relative_to를 사용하여 하위 경로가 맞는지 검증
        file_path.relative_to(resolved_dir)
    except ValueError:
        return Response({"status": 400, "message": "잘못된 접근입니다."}, status=400)

    # 파일 존재 여부 확인
    if not file_path.exists() or not file_path.is_file():
        return Response({"status": 404, "message": "요청하신 파일을 찾을 수 없습니다."}, status=404)

    # 파일을 스트리밍 응답으로 반환
    return FileResponse(open(file_path, 'rb'), content_type="model/gltf-binary")
