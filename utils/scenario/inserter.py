from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from lxml import etree as ET


@dataclass(frozen=True)
class ScenarioItem:
    tag_type: str       # "agent" | "actor" | "pos" | "speed" | "condition" | "behavior"
    ref_entity: str     # retrieval 기본값: "Target" (환경변수로 변경 가능)
    xml: str            # 삽입할 snippet


class InserterError(RuntimeError):
    pass


def insert_scenario(
    base_xosc_path: Path,
    items: Iterable[ScenarioItem],
) -> ET._ElementTree:
    """
    제시한 삽입 규칙 순서(agent -> pos/speed -> actor -> condition -> behavior)를 그대로 따른다.
    단, 데이터 입력은 generator/retrieval 인터페이스(ScenarioItem 리스트)에 맞춘다.
    """
    try:
        in_tree = ET.parse(str(base_xosc_path))
    except (OSError, ET.XMLSyntaxError) as e:
        raise InserterError(f"Failed to parse base_xosc_path={base_xosc_path}: {e}") from e

    root = copy.deepcopy(in_tree.getroot())
    tree = ET.ElementTree(root)
    response_data = list(items)

    # ---------- 기본 노드 확보 ----------
    entities = root.find(".//Entities")
    if entities is None:
        raise InserterError("Entities not found")

    storyboard = root.find(".//Storyboard")
    if storyboard is None:
        raise InserterError("Storyboard not found")

    init_actions = storyboard.find("./Init/Actions")
    if init_actions is None:
        raise InserterError("Storyboard/Init/Actions not found")

    act = storyboard.find("./Story/Act")
    if act is None:
        raise InserterError("Storyboard/Story/Act not found")

    maneuver_group = act.find("./ManeuverGroup")
    if maneuver_group is None:
        raise InserterError("Storyboard/Story/Act/ManeuverGroup not found")

    maneuver = maneuver_group.find("./Maneuver")
    if maneuver is None:
        raise InserterError("Storyboard/Story/Act/ManeuverGroup/Maneuver not found")

    # actor 기반 Event 구조
    action = None
    condition_group = None

    # ---------- agent ----------
    for item in response_data:
        if (item.tag_type or "").strip().lower() != "agent":
            continue

        # retrieval/generator와의 호환을 위해 ref_entity를 agent 이름으로 사용
        agent_name = (item.ref_entity or "").strip()
        if not agent_name:
            raise InserterError("agent ref_entity is required")

        try:
            agent_code = ET.fromstring((item.xml or "").strip().encode("utf-8"))
        except ET.XMLSyntaxError as e:
            raise InserterError(f"Invalid agent xml: {e}") from e

        entities.append(agent_code)

        private = init_actions.find(f"./Private[@entityRef='{agent_name}']")
        if private is None:
            ET.SubElement(init_actions, "Private", {"entityRef": agent_name})

    # ---------- pos / speed ----------
    for item in response_data:
        tag_type = (item.tag_type or "").strip().lower()
        if tag_type not in ("pos", "speed"):
            continue

        agent_name = (item.ref_entity or "").strip()
        if not agent_name:
            raise InserterError(f"{tag_type} ref_entity is required")

        try:
            code = ET.fromstring((item.xml or "").strip().encode("utf-8"))
        except ET.XMLSyntaxError as e:
            raise InserterError(f"Invalid {tag_type} xml: {e}") from e

        private = init_actions.find(f"./Private[@entityRef='{agent_name}']")
        if private is None:
            raise InserterError(f"Private not found for agent: {agent_name}")

        private.append(code)

    # ---------- actor ----------
    for item in response_data:
        if (item.tag_type or "").strip().lower() != "actor":
            continue

        actor_name = (item.ref_entity or "").strip()
        if not actor_name:
            raise InserterError("actor ref_entity is required")

        # 1) ScenarioObject 존재 여부 확인
        if entities.find(f"./ScenarioObject[@name='{actor_name}']") is None:
            raise InserterError(f"Actor '{actor_name}' not found in Entities")

        # 2) ManeuverGroup 속성 설정
        maneuver_group.set("name", f"{actor_name}ManeuverGroup")
        maneuver_group.set("actor", actor_name)

        # 3) 기존 Actors 제거
        for old in maneuver_group.findall("Actors"):
            maneuver_group.remove(old)

        # 4) Actors를 Maneuver 바로 앞에 삽입
        try:
            actors_elem = ET.fromstring((item.xml or "").strip().encode("utf-8"))
        except ET.XMLSyntaxError as e:
            raise InserterError(f"Invalid actor xml: {e}") from e

        maneuver = maneuver_group.find("Maneuver")
        if maneuver is None:
            raise InserterError("Maneuver not found under ManeuverGroup")

        idx = list(maneuver_group).index(maneuver)
        maneuver_group.insert(idx, actors_elem)

        # 5) Event 생성
        event = ET.SubElement(
            maneuver,
            "Event",
            {"name": f"{actor_name}Event", "priority": "override"},
        )

        # 6) Action 생성
        action = ET.SubElement(event, "Action", {"name": f"{actor_name}Action"})

        # 7) StartTrigger/ConditionGroup 생성
        start_trigger = ET.SubElement(event, "StartTrigger")
        condition_group = ET.SubElement(start_trigger, "ConditionGroup")

        # 샘플 정책 유지: actor 1개만 사용
        break

    # ---------- condition ----------
    for item in response_data:
        if (item.tag_type or "").strip().lower() != "condition":
            continue
        if condition_group is None:
            raise InserterError("ConditionGroup not initialized (actor missing)")

        try:
            condition_group.append(ET.fromstring((item.xml or "").strip().encode("utf-8")))
        except ET.XMLSyntaxError as e:
            raise InserterError(f"Invalid condition xml: {e}") from e

    # ---------- behavior ----------
    for item in response_data:
        if (item.tag_type or "").strip().lower() != "behavior":
            continue
        if action is None:
            raise InserterError("Action not initialized (actor missing)")

        try:
            action.append(ET.fromstring((item.xml or "").strip().encode("utf-8")))
        except ET.XMLSyntaxError as e:
            raise InserterError(f"Invalid behavior xml: {e}") from e

    ET.indent(tree, "  ")
    return tree
