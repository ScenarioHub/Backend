"""
xosc_parser.py
OpenSCENARIO (.xosc) 파일에서 차량 모델 매핑과 맵 경로를 추출하는 유틸리티.
"""
import os
from pathlib import Path
from lxml import etree as ET


def _get_node_from_catalog(catalog_name, entry_name, catalog_dirs, xosc_path, catalog_cache):
    if catalog_name not in catalog_dirs:
        return None
    
    rel_path = catalog_dirs[catalog_name]
    xosc_dir = Path(xosc_path).parent
    catalog_dir_path = (xosc_dir / rel_path).resolve()
    
    catalog_files = []
    if catalog_dir_path.is_file():
        catalog_files.append(catalog_dir_path)
    elif catalog_dir_path.is_dir():
        # 보통 <catalogName>.xosc 파일명 사용
        exact_file = catalog_dir_path / f"{catalog_name}.xosc"
        if exact_file.exists():
            catalog_files.append(exact_file)
        else:
            # 없으면 해당 디렉토리의 모든 xosc 검색
            catalog_files.extend(catalog_dir_path.glob("*.xosc"))
            
    for c_file in catalog_files:
        c_path_str = str(c_file)
        if c_path_str not in catalog_cache:
            try:
                c_tree = ET.parse(c_file)
                catalog_cache[c_path_str] = c_tree.getroot()
            except Exception:
                continue
                
        c_root = catalog_cache.get(c_path_str)
        if c_root is not None:
            # entry_name과 일치하는 요소(Vehicle, Pedestrian, MiscObject 등) 찾기
            for item in c_root.findall(f".//*[@name='{entry_name}']"):
                return item
    return None


def _extract_models_from_node(node, catalog_dirs, params, xosc_path, catalog_cache):
    models = []
    model_name = None
    
    # 1. 태그가 CatalogReference 이거나 직속 자식으로 가지고 있는 경우
    catalog_ref = node if node.tag == "CatalogReference" else node.find("CatalogReference")
    if catalog_ref is not None:
        catalog_name = catalog_ref.get("catalogName", "")
        entry_name = catalog_ref.get("entryName", "")
        
        if entry_name.startswith("$"):
            entry_name = params.get(entry_name[1:], entry_name)
            
        if catalog_name:
            resolved_node = _get_node_from_catalog(catalog_name, entry_name, catalog_dirs, xosc_path, catalog_cache)
            if resolved_node is not None:
                # 카탈로그에서 찾은 노드 (Vehicle, Pedestrian 등)를 재귀적으로 분석
                return _extract_models_from_node(resolved_node, catalog_dirs, params, xosc_path, catalog_cache)
                
        model_name = entry_name

    # 2. model3d 속성
    if model_name is None:
        model3d = node.get("model3d")
        if model3d:
            model_name = Path(model3d).stem

    # 3. Properties/File
    if model_name is None:
        file_prop = node.find(".//Properties/File")
        if file_prop is not None and file_prop.get("filepath"):
            model_name = Path(file_prop.get("filepath")).stem

    # 4. name 속성 (단, ScenarioObject가 아닐 때만. ScenarioObject의 name은 차량 종류가 아니라 인스턴스 이름임)
    if model_name is None and node.tag != "ScenarioObject":
        name_attr = node.get("name")
        if name_attr:
            model_name = name_attr

    # ScenarioObject 혹은 기타 래퍼일 때 직속 자식 검색
    if model_name is None and node.tag in ["ScenarioObject", "Vehicle"]:
        for child in node:
            if child.tag in ["Vehicle", "Pedestrian", "MiscObject"]:
                return _extract_models_from_node(child, catalog_dirs, params, xosc_path, catalog_cache)

    if model_name is None:
        model_name = "unknown"
        
    models.append(model_name)
    
    # Trailer 연쇄 탐색 (현재 노드 하위의 Trailer 안에 있는 Vehicle/CatalogReference 찾기)
    def find_trailer_models(curr_node):
        res = []
        for child in curr_node:
            if child.tag == "Trailer":
                res.extend(find_trailer_models(child))
            elif child.tag in ["Vehicle", "CatalogReference"]:
                res.extend(_extract_models_from_node(child, catalog_dirs, params, xosc_path, catalog_cache))
        return res

    if node.tag in ["Vehicle", "ScenarioObject"]:
        models.extend(find_trailer_models(node))
        
    return models


def extract_models(xosc_path):
    """
    xosc 파일에서 각 ScenarioObject의 차량 모델명을 추출한다.
    트레일러가 부착된 경우 esmini는 트레일러에도 별도의 Object ID를 부여하므로
    이를 반영하여 평활화(flatten)된 매핑 리스트를 생성한다.

    Returns:
        dict: {"0": "car_white", "1": "semi_tractor", "2": "semi_trailer", ...}
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

    # 1. CatalogLocations 파싱
    catalog_dirs = {}
    catalog_locations = root.find(".//CatalogLocations")
    if catalog_locations is not None:
        for catalog_type in catalog_locations:
            dir_node = catalog_type.find("Directory")
            if dir_node is not None and dir_node.get("path"):
                catalog_dirs[catalog_type.tag] = dir_node.get("path")
                
    catalog_cache = {}
    models = {}
    obj_id = 0
    
    entities = root.findall(".//Entities/ScenarioObject")
    for entity in entities:
        extracted = _extract_models_from_node(entity, catalog_dirs, params, xosc_path, catalog_cache)
        for m in extracted:
            models[str(obj_id)] = m
            obj_id += 1
            
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
