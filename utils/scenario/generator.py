# Backend/utils/scenario/generator.py
from __future__ import annotations

from pathlib import Path

from utils.scenario.retrieval import retrieve_scenario_items
from utils.scenario.inserter import insert_scenario
from utils.utils import save_scenario_file

from lxml import etree as ET


class ScenarioGenerationError(RuntimeError):
    pass


def generator(
    description: str,
    file_name: str,
    base_scenario_path: str,
) -> str:
    """
    Args:
        description: 자연어 설명
        file_name: 파일명(확장자 제외). 저장 시 ".xosc"만 붙임
        base_scenario_path: base xosc 파일 경로

    Returns:
        xosc_path (str)
    """

    base_xosc_path = Path(base_scenario_path)
    if not base_xosc_path.exists():
        raise ScenarioGenerationError(f"base xosc not found: {base_xosc_path}")

    # 1) 리소스 resolve
    base_xosc_path = base_xosc_path.resolve()
    
    # 2) snippet retrieval
    try:
        items = retrieve_scenario_items(description)
    except Exception as e:
        raise ScenarioGenerationError(f"Scenario retrieval failed: {e}") from e

    # 3) 삽입(템플릿 로드 + xodr 반영 + snippets 삽입)
    try:
        # insert_scenario는 ElementTree를 반환한다고 가정
        xosc_tree = insert_scenario(
            base_xosc_path=base_xosc_path,
            items=items,
        )
    except Exception as e:
        raise ScenarioGenerationError(f"XOSC insertion failed: {e}") from e

    try:
        # pretty_print는 선택. 서버에서 diff/디버깅 편하면 True
        xosc_bytes = ET.tostring(
            xosc_tree.getroot() if hasattr(xosc_tree, "getroot") else xosc_tree,
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=True,
        )
        xosc_path = save_scenario_file(xosc_bytes, file_name)
    except Exception as e:
        raise ScenarioGenerationError(f"Saving xosc failed: {e}") from e

    return xosc_path
