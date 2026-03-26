"""
xosc_parser.py
OpenSCENARIO (.xosc) 파일에서 차량 모델 매핑과 맵 경로를 추출하는 유틸리티.
"""
import os
from pathlib import Path
from lxml import etree as ET


def extract_vehicle_models(xosc_path):
    """
    xosc 파일에서 각 ScenarioObject의 차량 모델명을 추출한다.
    esmini는 Entities에 정의된 순서대로 object id를 0, 1, 2... 로 부여하므로
    동일한 순서로 매핑을 생성한다.

    Returns:
        dict: {"0": "car_white", "1": "car_red", ...}
    """
    tree = ET.parse(xosc_path)
    root = tree.getroot()

    # 최상위 ParameterDeclarations에서 파라미터 값 수집 (변수 치환용)
    params = {}
    for param in root.findall(".//ParameterDeclarations/ParameterDeclaration"):
        name = param.get("name")
        value = param.get("value")
        if name and value:
            params[name] = value

    models = {}
    entities = root.findall(".//Entities/ScenarioObject")

    for idx, entity in enumerate(entities):
        model_name = None

        # 1) CatalogReference에서 entryName 추출
        catalog_ref = entity.find(".//CatalogReference")
        if catalog_ref is not None:
            entry_name = catalog_ref.get("entryName", "")
            # $변수 참조 치환
            if entry_name.startswith("$"):
                param_key = entry_name[1:]
                model_name = params.get(param_key, entry_name)
            else:
                model_name = entry_name

        # 2) ScenarioObject의 자식 태그들(Vehicle, Pedestrian 등) 검색
        if model_name is None:
            # 보통 Vehicle이나 Pedestrian 태그가 1개 존재
            for child in entity:
                if child.tag == "CatalogReference":
                    continue
                
                # 1. model3d 속성 먼저 확인 (우선순위 높음)
                model3d = child.get("model3d")
                if model3d:
                    model_name = Path(model3d).stem
                    break

                # 2. Properties/File[@filepath] 확인
                file_prop = child.find(".//Properties/File")
                if file_prop is not None:
                    filepath = file_prop.get("filepath")
                    if filepath:
                        model_name = Path(filepath).stem
                        break

        if model_name is None:
            model_name = "unknown"

        models[str(idx)] = model_name

    return models


def extract_map_xodr_path(xosc_path):
    """
    xosc 파일에서 RoadNetwork/LogicFile의 filepath를 읽어
    xodr 파일의 절대 경로를 반환한다.

    Returns:
        str: xodr 파일 절대 경로
    """
    tree = ET.parse(xosc_path)
    root = tree.getroot()

    logic_file = root.find(".//RoadNetwork/LogicFile")
    if logic_file is None:
        raise ValueError(f"xosc 파일에서 RoadNetwork/LogicFile을 찾을 수 없습니다: {xosc_path}")

    filepath = logic_file.get("filepath", "")
    if not filepath:
        raise ValueError(f"LogicFile filepath가 비어있습니다: {xosc_path}")

    # 상대경로인 경우 xosc 파일 기준으로 절대경로 변환
    xodr_path = Path(filepath)
    if not xodr_path.is_absolute():
        xosc_dir = Path(xosc_path).parent
        xodr_path = (xosc_dir / filepath).resolve()

    return str(xodr_path)
