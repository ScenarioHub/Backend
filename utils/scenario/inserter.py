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

    ET.indent(tree, "  ")
    return tree


# -----------------------------
# Core insertion routing
# -----------------------------
def _insert_item(root: ET._Element, item: ScenarioItem) -> None:
    t = (item.tag_type or "").strip().lower()
    if not t:
        return

    frag = _parse_fragment(item.xml)

    if t == "agent":
        _insert_agent(root, frag)
        return

    if t in ("pos", "speed"):
        _insert_into_init_actions_private(root, item.ref_entity, frag)
        return

    if t == "actor":
        _insert_actor(root, item.ref_entity, frag)
        return

    if t in ("condition",):
        _insert_condition(root, item.ref_entity, frag)
        return

    if t in ("behavior",):
        _insert_behavior(root, item.ref_entity, frag)
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


def _insert_agent(root: ET._Element, frag: list[ET._Element]) -> None:
    """
    agent:
      1) Entities 하위에 삽입
      2) Storyboard/Init/Actions 하위에 <Private entityRef="agent 이름"> 생성
    """
    _insert_into_entities(root, frag)

    for name in _extract_scenario_object_names(frag):
        _ensure_private_entity(root, name)


def _insert_actor(root: ET._Element, entity_ref: str, frag: list[ET._Element]) -> None:
    """
    actor:
      1) actor 이름 ScenarioObject 존재 확인
      2) Story/Act/ManeuverGroup 하위 삽입
      3~6) Maneuver/Event/Action/StartTrigger/ConditionGroup 구조 보장
    """
    ref = (entity_ref or "").strip()
    if not ref:
        raise InserterError("actor ref_entity is required")

    if not _scenario_object_exists(root, ref):
        raise InserterError(f"actor ScenarioObject not found: {ref}")

    mg, _, _, _, _ = _ensure_story_chain(root, ref)
    for el in frag:
        # Actors wrapper가 오면 중복 생성 대신 EntityRef만 보강
        if el.tag == "Actors":
            for er in el.findall(".//EntityRef"):
                er_name = (er.get("entityRef") or "").strip()
                if er_name:
                    _ensure_maneuver_group_for_entity(root, er_name)
            if not list(el.findall(".//EntityRef")):
                mg.append(_clone(el))
            continue
        mg.append(_clone(el))


def _insert_condition(root: ET._Element, entity_ref: str, frag: list[ET._Element]) -> None:
    """
    condition:
      Story/Act/ManeuverGroup/Maneuver/Event/StartTrigger/ConditionGroup 하위 삽입
    """
    ref = (entity_ref or "Target").strip() or "Target"
    _, _, _, _, cond_group = _ensure_story_chain(root, ref)
    for el in frag:
        if el.tag == "ConditionGroup":
            for c in list(el):
                cond_group.append(_clone(c))
        else:
            cond_group.append(_clone(el))


def _insert_behavior(root: ET._Element, entity_ref: str, frag: list[ET._Element]) -> None:
    """
    behavior:
      Story/Act/ManeuverGroup/Maneuver/Event/Action 하위 삽입
    """
    ref = (entity_ref or "Target").strip() or "Target"
    _, _, _, action, _ = _ensure_story_chain(root, ref)
    for el in frag:
        if el.tag == "Action":
            for c in list(el):
                action.append(_clone(c))
        else:
            action.append(_clone(el))


def _insert_into_init_actions_private(root: ET._Element, entity_ref: str, frag: list[ET._Element]) -> None:
    """
    Storyboard/Init/Actions 아래에 Private(entityRef=...)가 없으면 만들고,
    그 아래에 fragment를 적절히 삽입.

    - snippet이 <Private entityRef="...">이면 그 내부 children을 이 entityRef Private에 병합
    - snippet이 <PrivateAction> / <LongitudinalAction> 등이라면 Private 아래에 바로 append
    """
    if not entity_ref:
        entity_ref = "Target"

    priv = _ensure_private_entity(root, entity_ref)

    for el in frag:
        if el.tag == "Private":
            # entityRef 상관없이 내부를 병합(템플릿 private에 넣는 정책)
            for c in list(el):
                priv.append(_clone(c))
        else:
            priv.append(_clone(el))


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
    return mg


def _ensure_private_entity(root: ET._Element, entity_ref: str) -> ET._Element:
    actions = root.find(".//Storyboard/Init/Actions")
    if actions is None:
        storyboard = root.find(".//Storyboard")
        if storyboard is None:
            storyboard = _ensure_path(root, ["Storyboard"])
        init = _find_or_create(storyboard, "Init")
        actions = _find_or_create(init, "Actions")

    for p in actions.findall("Private"):
        if p.get("entityRef") == entity_ref:
            return p
    return ET.SubElement(actions, "Private", entityRef=entity_ref)


def _extract_scenario_object_names(frag: list[ET._Element]) -> list[str]:
    names: list[str] = []
    for el in frag:
        if el.tag == "ScenarioObject":
            n = (el.get("name") or "").strip()
            if n:
                names.append(n)
            continue
        for so in el.findall(".//ScenarioObject"):
            n = (so.get("name") or "").strip()
            if n:
                names.append(n)
    # 중복 제거(순서 유지)
    seen = set()
    out: list[str] = []
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def _scenario_object_exists(root: ET._Element, name: str) -> bool:
    return root.find(f".//Entities/ScenarioObject[@name='{name}']") is not None


def _ensure_maneuver_group_for_entity(root: ET._Element, entity_ref: str) -> ET._Element:
    act = root.find(".//Storyboard/Story/Act")
    if act is None:
        act = _ensure_default_act(root)
    mg = _find_maneuver_group_for_entity(act, entity_ref)
    if mg is None:
        mg = _create_maneuver_group(act, entity_ref)
    return mg


def _ensure_story_chain(root: ET._Element, entity_ref: str) -> tuple[ET._Element, ET._Element, ET._Element, ET._Element, ET._Element]:
    """
    Story -> Act -> ManeuverGroup -> Maneuver -> Event -> Action / StartTrigger -> ConditionGroup
    """
    mg = _ensure_maneuver_group_for_entity(root, entity_ref)

    maneuver = mg.find("Maneuver")
    if maneuver is None:
        maneuver = ET.SubElement(mg, "Maneuver", name=f"Maneuver_{entity_ref}")

    event = maneuver.find("Event")
    if event is None:
        event = ET.SubElement(maneuver, "Event", name=f"Event_{entity_ref}", priority="override")

    action = event.find("Action")
    if action is None:
        action = ET.SubElement(event, "Action", name=f"Action_{entity_ref}")

    start_trigger = event.find("StartTrigger")
    if start_trigger is None:
        start_trigger = ET.SubElement(event, "StartTrigger")

    cond_group = start_trigger.find("ConditionGroup")
    if cond_group is None:
        cond_group = ET.SubElement(start_trigger, "ConditionGroup")

    return mg, maneuver, event, action, cond_group
