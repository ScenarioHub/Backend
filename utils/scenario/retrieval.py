from __future__ import annotations

import os
import json
import re
import logging
import threading
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import psycopg
from django.conf import settings

from utils.scenario.inserter import ScenarioItem


class RetrievalError(RuntimeError):
    pass

logger = logging.getLogger(__name__)


# -----------------------------
# Config
# -----------------------------
PARTS = ["actors", "agents", "positions", "speeds", "conditions", "behaviors"]

TAG_TYPE_MAP = {
    "actors": "actor",
    "agents": "agent",
    "positions": "pos",
    "speeds": "speed",
    "conditions": "condition",
    "behaviors": "behavior",
}

# 각 파트 테이블에서 snippet xml이 들어있는 컬럼명
XML_COL_MAP = {p: "code" for p in PARTS}

# 2-stage retrieval
STAGE1_TOPK = int(os.environ.get("SCENARIO_STAGE1_TOPK", "20"))

# entityRef 기본값(템플릿 Entities에 있는 이름과 일치해야 함)
DEFAULT_REF_ENTITY = os.environ.get("SCENARIO_DEFAULT_ENTITY", "Target")

# 임베딩 입력 prefix(선택)
PREFIX = os.environ.get("SCENARIO_EMB_PREFIX", "DESC: ").strip()

# Gemini 설정
GEMINI_API_KEY = settings.GEMINI_API_KEY
GEMINI_MODEL = "gemini-2.5-flash"

NORMALIZE = True


# -----------------------------
# Model cache (bge-m3)
# -----------------------------
_MODEL = None
_MODEL_LOCK = threading.Lock()


def _get_model():
    """
    서버 프로세스에서 1회만 로드.
    """
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL

        try:
            from FlagEmbedding import FlagAutoModel
        except Exception as e:
            raise RetrievalError(f"FlagEmbedding not available: {e}") from e

        # 운영 환경이 CPU일 수도 있으니 실패하면 fp16 끄고 재시도
        try:
            _MODEL = FlagAutoModel.from_finetuned("BAAI/bge-m3", use_fp16=True)
        except Exception:
            _MODEL = FlagAutoModel.from_finetuned("BAAI/bge-m3", use_fp16=False)

        return _MODEL


# -----------------------------
# Public API
# -----------------------------
def retrieve_scenario_items(description: str) -> List[ScenarioItem]:
    """
    description 기반으로 DB(pgvector)에서 파트별 snippet을 하나씩 골라서 ScenarioItem 리스트로 반환.

    반환되는 item.tag_type은 inserter.py의 라우팅 규칙과 맞아야 한다:
      "agent", "actor", "pos", "speed", "condition", "behavior"
    """
    desc = (description or "").strip()
    if not desc:
        raise RetrievalError("description is empty")

    cfg = _build_query_cfg(desc)

    dsn = _get_db_dsn()
    model = _get_model()

    total_vec = _encode_dense(model, cfg["total"])
    if total_vec is None:
        raise RetrievalError("failed to embed total description")
    total_vec_pg = _vec_to_pg(total_vec)

    items: List[ScenarioItem] = []

    with psycopg.connect(dsn) as conn:
        for part in PARTS:
            qtext = (cfg.get(part) or "").strip()

            # 파트별 쿼리가 비어있으면 total로 대체해서 최소 1개는 나오도록
            if not qtext:
                qtext = cfg["total"]

            qvec = _encode_dense(model, qtext)
            if qvec is None:
                continue
            qvec_pg = _vec_to_pg(qvec)

            try:
                cand_ids = _stage1_candidate_ids(conn, table=part, qvec_pg=qvec_pg, topk=STAGE1_TOPK)
                xml = _stage2_pick1_xml(
                    conn,
                    table=part,
                    total_vec_pg=total_vec_pg,
                    candidate_ids=cand_ids,
                    xml_col=XML_COL_MAP[part],
                )
            except Exception as e:
                raise RetrievalError(f"DB retrieval failed for part={part}: {e}") from e

            if not xml:
                continue

            items.append(
                ScenarioItem(
                    tag_type=TAG_TYPE_MAP[part],
                    ref_entity=DEFAULT_REF_ENTITY,
                    xml=str(xml).strip(),
                )
            )

    return items


# -----------------------------
# Query parts builder (placeholder)
# -----------------------------
def _build_query_cfg(description: str) -> Dict[str, str]:
    """
    LLM 분해만 사용한다.
    LLM 접근/파싱 실패 시 RetrievalError를 발생시킨다.
    """
    desc = description.strip()

    llm_cfg = _build_query_cfg_llm(desc)
    if llm_cfg is None:
        logger.error("LLM query split failed; fallback is disabled.")
        raise RetrievalError("LLM query split failed")

    return llm_cfg


def _build_query_cfg_llm(description: str) -> Optional[Dict[str, str]]:
    """
    Gemini API를 사용해 description을 파트별 텍스트로 분해한다.
    실패 시 None 반환.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is missing; cannot access LLM.")
        return None

    prompt = _load_gemini_prompt(description)

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512,
        },
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        logger.exception("Gemini API request failed.")
        return None

    try:
        text = (
            data["candidates"][0]["content"]["parts"][0]["text"]
            if data.get("candidates")
            else ""
        )
        text = (text or "").strip()
        if not text:
            logger.error("Gemini API returned empty text.")
            return None

        # LLM이 코드블록으로 감쌀 수 있으니 제거
        if text.startswith("```"):
            text = text.strip("`")
            # 간단히 첫/마지막 라인 제거
            lines = [ln for ln in text.splitlines() if ln.strip()]
            if len(lines) >= 2:
                text = "\n".join(lines[1:])

        cfg = json.loads(text)
    except Exception:
        logger.exception("Failed to parse Gemini response JSON.")
        return None

    # 키 보정
    keys = ["total", "actors", "agents", "positions", "speeds", "conditions", "behaviors"]
    out: Dict[str, str] = {}
    for k in keys:
        v = cfg.get(k, "")
        out[k] = str(v).strip() if v is not None else ""
    if not out.get("total"):
        out["total"] = description
    return out


def _load_gemini_prompt(description: str) -> str:
    """
    프롬프트를 파일에서 불러오고, 없으면 기본 문자열 사용.
    """
    default_prompt = (
        "You are a parser that extracts scenario info into fixed JSON fields.\n"
        "Return ONLY a JSON object with keys:\n"
        "total, actors, agents, positions, speeds, conditions, behaviors.\n"
        "Rules:\n"
        "- Always include all keys.\n"
        "- Use empty string if unknown.\n"
        "- Do not add extra keys or commentary.\n"
        "- Keep values short and specific.\n"
        "- Keep language same as input.\n\n"
        "Input:\n{description}\n\n"
        "Output must be raw JSON only."
    )

    prompt_path = Path(__file__).resolve().parent / "prompts" / "gemini_split.txt"
    try:
        text = prompt_path.read_text(encoding="utf-8")
    except Exception:
        text = default_prompt

    return text.replace("{description}", description)

def _extract_speed(text: str) -> Optional[str]:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(m/s|mps)", text, re.IGNORECASE)
    if not m:
        return None
    return m.group(0).strip()


def _extract_position(text: str) -> Optional[str]:
    m = re.search(r"(\d+(?:\.\d+)?)\s*m\s*지점", text)
    if not m:
        return None
    return m.group(0).strip()


# -----------------------------
# DB helpers
# -----------------------------
def _get_db_dsn() -> str:
    """
    우선순위:
      1) 환경변수 DB_DSN
      2) Django settings.DB_DSN (있다면)
    """
    dsn = os.environ.get("DB_DSN", "").strip()
    if dsn:
        return dsn
    dsn = getattr(settings, "DB_DSN", "").strip()
    if dsn:
        return dsn
    raise RetrievalError("DB_DSN is not set (env DB_DSN or settings.DB_DSN)")


def _stage1_candidate_ids(conn: psycopg.Connection, table: str, qvec_pg: str, topk: int) -> List[int]:
    # TODO
    # sql = f"""
    #     SELECT id
    #     FROM scenario_snippet.{table}
    #     WHERE embedding IS NOT NULL
    #     ORDER BY embedding <=> %s::vector
    #     LIMIT %s;
    # """
    sql = f"""
        SELECT id
        FROM public.{table}
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (qvec_pg, topk))
        return [row[0] for row in cur.fetchall()]


def _stage2_pick1_xml(
    conn: psycopg.Connection,
    table: str,
    total_vec_pg: str,
    candidate_ids: List[int],
    xml_col: str,
) -> Optional[str]:
    if not candidate_ids:
        return None

    # TODO
    # sql = f"""
    #     SELECT {xml_col}
    #     FROM scenario_snippet.{table}
    #     WHERE id = ANY(%s)
    #     ORDER BY embedding <=> %s::vector
    #     LIMIT 1;
    # """
    sql = f"""
        SELECT {xml_col}
        FROM public.{table}
        WHERE id = ANY(%s)
        ORDER BY embedding <=> %s::vector
        LIMIT 1;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_ids, total_vec_pg))
        row = cur.fetchone()
        return row[0] if row else None


# -----------------------------
# Embedding helpers
# -----------------------------
def _to_numpy(x):
    if hasattr(x, "detach"):
        return x.detach().cpu().numpy()
    return np.asarray(x)


def _l2_normalize(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / (n + eps)


def _encode_dense(model, text: str) -> Optional[np.ndarray]:
    t = (text or "").strip()
    if not t:
        return None

    inp = (PREFIX + t) if PREFIX else t
    out = model.encode([inp])

    vecs = out["dense_vecs"] if isinstance(out, dict) else out
    v = _to_numpy(vecs)[0].astype(np.float32)

    if NORMALIZE:
        v = _l2_normalize(v)

    return v


def _vec_to_pg(v: np.ndarray) -> str:
    """
    pgvector 입력 포맷: [0.1,0.2,...]
    """
    return "[" + ",".join(f"{x:.8f}" for x in v.tolist()) + "]"
