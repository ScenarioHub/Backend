# Backend/utils/scenario/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ScenarioConfigError(RuntimeError):
    pass


def _find_repo_root(start: Path) -> Path:
    """
    Backend/utils/scenario/config.py 위치에서 시작해서
    'Backend' 디렉토리를 기준으로 프로젝트 루트(SCENARIOHUB/)를 추정한다.

    기대 구조:
      <REPO_ROOT>/
        Backend/
          utils/scenario/config.py
        data/
          xodr/
          xosc/
    """
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if p.name == "Backend" and (p.parent / "data").exists():
            return p.parent
    # fallback: config.py의 상위 3~5단계 어딘가에 data가 있는지 탐색
    for p in [cur, *cur.parents]:
        if (p / "data").exists():
            return p
    raise ScenarioConfigError(
        "Cannot locate repo root. Set SCENARIO_DATA_DIR env var or ensure '<repo>/data' exists."
    )


def _safe_join(base_dir: Path, name: str, allow_suffixes: tuple[str, ...]) -> Path:
    """
    name은 파일명 또는 상대경로(하위 폴더 포함)까지만 허용.
    절대경로/상위경로(../)는 차단한다.
    """
    if not name or not str(name).strip():
        raise ScenarioConfigError("Empty name is not allowed.")

    name = name.strip()

    # 절대경로 차단
    p = Path(name)
    if p.is_absolute():
        raise ScenarioConfigError(f"Absolute path is not allowed: {name}")

    # suffix 검사
    if allow_suffixes:
        if p.suffix.lower() not in allow_suffixes:
            raise ScenarioConfigError(
                f"Invalid file extension: {p.suffix}. Allowed: {allow_suffixes}"
            )

    # base_dir 아래로만 resolve되게 강제 (path traversal 방지)
    full = (base_dir / p).resolve()
    base_resolved = base_dir.resolve()
    if base_resolved not in full.parents and full != base_resolved:
        raise ScenarioConfigError(f"Path traversal detected: {name}")

    return full


@dataclass(frozen=True)
class ScenarioPaths:
    """
    서버 리소스 경로들.
    """
    data_dir: Path
    xodr_dir: Path
    xosc_dir: Path
    generated_dir: Path


def load_paths() -> ScenarioPaths:
    """
    우선순위:
      1) 환경변수 SCENARIO_DATA_DIR
      2) 코드 위치 기준 repo 루트 탐색 후 <repo>/data
    """
    env = os.environ.get("SCENARIO_DATA_DIR", "").strip()
    if env:
        data_dir = Path(env).expanduser().resolve()
    else:
        repo_root = _find_repo_root(Path(__file__))
        data_dir = (repo_root / "data").resolve()

    xodr_dir = data_dir / "xodr"
    xosc_dir = data_dir / "xosc"
    generated_dir = data_dir / "scenario" / "generated"

    # 필수 디렉토리 점검 (없으면 명확히 에러)
    if not xodr_dir.exists():
        raise ScenarioConfigError(f"Missing xodr dir: {xodr_dir}")
    if not xosc_dir.exists():
        raise ScenarioConfigError(f"Missing xosc dir: {xosc_dir}")

    # generated는 없으면 생성(운영 편의)
    generated_dir.mkdir(parents=True, exist_ok=True)

    return ScenarioPaths(
        data_dir=data_dir,
        xodr_dir=xodr_dir,
        xosc_dir=xosc_dir,
        generated_dir=generated_dir,
    )


# 모듈 로드시 1회 로딩(원하면 generator에서 load_paths() 호출해도 됨)
PATHS = load_paths()


def resolve_xodr(xodr_name: str) -> Path:
    """
    예: "Town01.xodr" 또는 "maps/Town01.xodr"
    """
    p = _safe_join(PATHS.xodr_dir, xodr_name, allow_suffixes=(".xodr",))
    if not p.exists():
        raise ScenarioConfigError(f"xodr not found: {p}")
    return p


def resolve_base_xosc(base_xosc_name: str) -> Path:
    """
    예: "straight_500m.xosc" 또는 "base/straight_500m.xosc"
    """
    p = _safe_join(PATHS.xosc_dir, base_xosc_name, allow_suffixes=(".xosc",))
    if not p.exists():
        raise ScenarioConfigError(f"base xosc not found: {p}")
    return p


def new_generated_xosc_path(filename: str | None = None) -> Path:
    """
    생성 결과 저장 경로 생성.
    filename이 없으면 UUID로 생성하도록 storage.py에서 덮어써도 됨.
    """
    if filename is None:
        # storage.py에서 uuid로 생성하는 걸 권장하므로 기본은 placeholder
        filename = "generated.xosc"
    if not filename.endswith(".xosc"):
        filename += ".xosc"
    p = (PATHS.generated_dir / filename).resolve()
    return p