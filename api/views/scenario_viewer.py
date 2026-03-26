
import os
from pathlib import Path

from django.conf import settings
from django.db import connection
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from api.auth.decorators import jwt_auth_optional
from utils.xosc_parser import extract_models, extract_map_xodr_path
from utils.utils import xodr2glb, run_esmini_simulation, dat2csv, csv2dict


@swagger_auto_schema(
    method="GET",
    operation_summary="시나리오 뷰어",
    operation_description="웹 인터랙티브 뷰를 위해 필요한 데이터를 조회합니다.",
    responses={
        200: openapi.Response(
            description="조회 성공",
            examples={
                'application/json': {
                    "status": 200,
                    "message": {
                        "scenario" : {
                            "0.0": {
                                "0": {
                                    "x": 8.173,
                                    "y": 49.97,
                                    "z": -0.041,
                                    "h": 1.567
                                },
                                "1": {
                                    "x": 4.51,
                                    "y": 24.985,
                                    "z": -0.011,
                                    "h": 1.567
                                }
                            },
                            "0.033": {
                                "0": {
                                    "x": 8.177,
                                    "y": 50.96,
                                    "z": -0.042,
                                    "h": 1.567
                                },
                                "1": {
                                    "x": 4.51,
                                    "y": 24.985,
                                    "z": -0.011,
                                    "h": 1.567
                                }
                            },
                        },
                        "models" : {
                            "0" : "/contents/models-glb/car_white.glb",
                            "1" : "/contents/models-glb/car_red.glb"
                        },
                        "map" : "/contents/xodr-glb/crest-curve.glb"
                    }
                }
            }
        ),
        404: openapi.Response(description="시나리오를 찾을 수 없음"),
        500: openapi.Response(description="시뮬레이션 처리 중 오류"),
    }
)
@api_view(["GET"])
@jwt_auth_optional
@authentication_classes([])
@permission_classes([])
def scenario_viewer(request, scenarioId):
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT file_url FROM scenarios WHERE id = %s",
            [scenarioId]
        )
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return Response({"status": 404, "message": "시나리오를 찾을 수 없습니다."}, status=404)

        xosc_path = row[0]
        if not os.path.exists(xosc_path):
            return Response({"status": 404, "message": f"시나리오 파일을 찾을 수 없습니다: {xosc_path}"}, status=404)

        sim_dir = settings.DATA_ROOT / "esmini_sim"
        models_dir = settings.DATA_ROOT / "models_glb"
        glb_dir = settings.DATA_ROOT / "xodr_glb"

        xosc_stem = Path(xosc_path).stem
        dat_path = sim_dir / f"{xosc_stem}.dat"

        models = extract_models(xosc_path)
        print(models)
        model_urls = {}
        for obj_id, model_name in models.items():
            print(model_name)
            model_urls[obj_id] = f"/contents/models-glb/{model_name}.glb"

        run_esmini_simulation(xosc_path, dat_path)
        csv_path = dat2csv(dat_path)
        scenario_data = csv2dict(csv_path)

        xodr_path = extract_map_xodr_path(xosc_path)
        xodr_stem = Path(xodr_path).stem
        xodr_glb = glb_dir / f"{xodr_stem}.glb"
        xodr2glb(str(xodr_path), str(xodr_glb))

        response_data = {
            "status": 200,
            "message": {
                "scenario": scenario_data,
                "models": model_urls,
                "map": f"/contents/xodr-glb/{xodr_stem}.glb",
            }
        }

        return Response(
            data=response_data,
            status=200
        )

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        
        return Response(
            {"status": 500, "message": f"시뮬레이션 처리 중 오류가 발생했습니다: {str(e)}"},
            status=500
        )
