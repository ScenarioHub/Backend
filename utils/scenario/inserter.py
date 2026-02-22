# Backend/utils/scenario/inserter.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union

from lxml import etree as ET


# retrieval 쪽에서 동일한 스키마를 쓰는 걸 추천(중복 정의 방지)
@dataclass(frozen=True)
class ScenarioItem:
    tag_type: str       # "agent" | "actor" | "pos" | "speed" | "condition" | "behavior"
    ref_entity: str     # 예: "Target"
    xml: str            # 삽입할 snippet (단일 element 또는 fragment)


class InserterError(RuntimeError):
    pass


# -----------------------------
# Public API
# -----------------------------
def insert_scenario(
    base_xosc_path: Path,
    items: Iterable[ScenarioItem],
) -> ET._ElementTree:
    """
    base xosc를 로드하고,
    items를 tag_type에 맞는 위치에 삽입한다.

    Returns:
        lxml ElementTree
    """
    tree = ET.parse(str(base_xosc_path))
    root = tree.getroot()

    for it in items:
        _insert_item(root, it)

    return tree


# -----------------------------
# Core insertion routing
# -----------------------------
def _insert_item(root: ET._Element, item: ScenarioItem) -> None:
    t = (item.tag_type or "").strip().lower()
    if not t:
        return

    frag = _parse_fragment(item.xml)

    if t in ("agent", "actor"):
        _insert_into_entities(root, frag)
        return

    if t in ("pos", "speed"):
        _insert_into_init_actions_private(root, item.ref_entity, frag)
        return

    if t in ("condition",):
        _insert_into_start_trigger(root, frag)
        return

    if t in ("behavior",):
        _insert_into_maneuver_group(root, item.ref_entity, frag)
        return

    # 알 수 없는 타입이면 최대한 안전하게 버림(혹은 raise)
    raise InserterError(f"Unknown tag_type: {item.tag_type}")


# -----------------------------
# Section creators / finders
# -----------------------------
def _find_or_create(parent: ET._Element, tag: str) -> ET._Element:
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    return node


def _ensure_path(root: ET._Element, tags: list[str]) -> ET._Element:
    """
    root 아래로 tags 순서대로 없으면 생성하면서 내려감.
    """
    cur = root
    for tg in tags:
        cur = _find_or_create(cur, tg)
    return cur


# -----------------------------
# Fragment parsing (robust)
# -----------------------------
def _parse_fragment(xml: str) -> list[ET._Element]:
    """
    DB snippet이 아래 어느 형태든 최대한 파싱:
    1) 단일 element 문자열: "<ScenarioObject .../>"
    2) 여러 element fragment: "<A/> <B/>"
    3) 이미 Private/ConditionGroup 같은 wrapper 포함
    """
    s = (xml or "").strip()
    if not s:
        return []

    # 여러 루트가 있을 수 있으니 wrapper로 감싼 뒤 children을 꺼냄
    wrapped = f"<__wrap__>{s}</__wrap__>"
    try:
        wrap_root = ET.fromstring(wrapped.encode("utf-8"))
    except ET.XMLSyntaxError as e:
        raise InserterError(f"Invalid snippet xml: {e}\nSnippet:\n{s[:400]}") from e

    return [child for child in wrap_root]


def _clone(e: ET._Element) -> ET._Element:
    # lxml에서 재사용 삽입하면 원본이 이동하므로 deepcopy 필요
    return ET.fromstring(ET.tostring(e))


# -----------------------------
# Insert targets
# -----------------------------
def _insert_into_entities(root: ET._Element, frag: list[ET._Element]) -> None:
    """
    Entities 아래에 ScenarioObject/EntitySelection 등을 넣는 용도.
    snippet이 <Entities> wrapper면 children만 꺼내서 append.
    """
    entities = root.find(".//Entities")
    if entities is None:
        entities = _ensure_path(root, ["Entities"])

    for el in frag:
        # snippet이 <Entities>면 내부만 넣는다
        if el.tag == "Entities":
            for c in list(el):
                entities.append(_clone(c))
        else:
            entities.append(_clone(el))


def _insert_into_init_actions_private(root: ET._Element, entity_ref: str, frag: list[ET._Element]) -> None:
    """
    Storyboard/Init/Actions 아래에 Private(entityRef=...)가 없으면 만들고,
    그 아래에 fragment를 적절히 삽입.

    - snippet이 <Private entityRef="...">이면 그 내부 children을 이 entityRef Private에 병합
    - snippet이 <PrivateAction> / <LongitudinalAction> 등이라면 Private 아래에 바로 append
    """
    if not entity_ref:
        entity_ref = "Target"

    actions = root.find(".//Storyboard/Init/Actions")
    if actions is None:
        # Storyboard/Init/Actions가 템플릿에 없으면 생성
        storyboard = root.find(".//Storyboard")
        if storyboard is None:
            storyboard = _ensure_path(root, ["Storyboard"])
        init = _find_or_create(storyboard, "Init")
        actions = _find_or_create(init, "Actions")

    # Private 찾거나 생성
    priv = None
    for p in actions.findall("Private"):
        if p.get("entityRef") == entity_ref:
            priv = p
            break
    if priv is None:
        priv = ET.SubElement(actions, "Private", entityRef=entity_ref)

    for el in frag:
        if el.tag == "Private":
            # entityRef 상관없이 내부를 병합(템플릿 private에 넣는 정책)
            for c in list(el):
                priv.append(_clone(c))
        else:
            priv.append(_clone(el))


def _insert_into_start_trigger(root: ET._Element, frag: list[ET._Element]) -> None:
    """
    Storyboard/Story/Act/StartTrigger에 ConditionGroup/Condition 등을 삽입.
    템플릿 구조가 다양해서 Act가 없으면 기본 Act를 생성한다.
    """
    start_trigger = root.find(".//Storyboard/Story/Act/StartTrigger")
    if start_trigger is None:
        act = _ensure_default_act(root)
        start_trigger = _find_or_create(act, "StartTrigger")

    for el in frag:
        if el.tag == "StartTrigger":
            for c in list(el):
                start_trigger.append(_clone(c))
        elif el.tag == "ConditionGroup":
            start_trigger.append(_clone(el))
        elif el.tag == "Condition":
            # Condition 단독이면 ConditionGroup으로 감싼다 (표준 구조)
            cg = ET.Element("ConditionGroup")
            cg.append(_clone(el))
            start_trigger.append(cg)
        else:
            # 알 수 없으면 일단 trigger 아래로 붙임(최대한 관대)
            start_trigger.append(_clone(el))


def _insert_into_maneuver_group(root: ET._Element, entity_ref: str, frag: list[ET._Element]) -> None:
    """
    Storyboard/Story/Act 아래 ManeuverGroup을 찾아(없으면 생성) snippet 삽입.
    behavior snippet이 Maneuver/ManeuverGroup/Event/Action 등 여러 형태일 수 있으니 최대한 수용.
    """
    if not entity_ref:
        entity_ref = "Target"

    act = root.find(".//Storyboard/Story/Act")
    if act is None:
        act = _ensure_default_act(root)

    # ManeuverGroup 찾기(Actor/EntityRef 기준이 템플릿마다 다름)
    mg = _find_maneuver_group_for_entity(act, entity_ref)
    if mg is None:
        mg = _create_maneuver_group(act, entity_ref)

    for el in frag:
        if el.tag == "ManeuverGroup":
            # 통째로 오면 내부를 병합
            for c in list(el):
                mg.append(_clone(c))
        else:
            mg.append(_clone(el))


def _ensure_default_act(root: ET._Element) -> ET._Element:
    """
    Storyboard/Story/Act가 없을 경우 최소 구조로 생성.
    """
    storyboard = root.find(".//Storyboard")
    if storyboard is None:
        storyboard = _ensure_path(root, ["Storyboard"])

    story = storyboard.find("Story")
    if story is None:
        story = ET.SubElement(storyboard, "Story", name="Story_1")

    act = story.find("Act")
    if act is None:
        act = ET.SubElement(story, "Act", name="Act_1")

    return act


def _find_maneuver_group_for_entity(act: ET._Element, entity_ref: str) -> Optional[ET._Element]:
    """
    ManeuverGroup 내부의 Actors/EntityRef 또는 Actor 태그 유무가 템플릿마다 다르므로
    여러 케이스를 체크한다.
    """
    for mg in act.findall(".//ManeuverGroup"):
        # Case 1: <Actors><EntityRef entityRef="Target"/></Actors>
        for er in mg.findall(".//Actors/EntityRef"):
            if er.get("entityRef") == entity_ref:
                return mg
        # Case 2: <Actors><Actor entityRef="Target"/></Actors> (비표준/커스텀 가능)
        for er in mg.findall(".//Actors/Actor"):
            if er.get("entityRef") == entity_ref:
                return mg
    return None


def _create_maneuver_group(act: ET._Element, entity_ref: str) -> ET._Element:
    """
    최소 ManeuverGroup 구조를 생성한다.
    """
    mg = ET.SubElement(act, "ManeuverGroup", name=f"MG_{entity_ref}", maximumExecutionCount="1")
    actors = ET.SubElement(mg, "Actors", selectTriggeringEntities="false")
    ET.SubElement(actors, "EntityRef", entityRef=entity_ref)
    # Maneuver는 behavior가 들어갈 때 생성될 수도 있어서 여기서는 비워둠
    return mg
