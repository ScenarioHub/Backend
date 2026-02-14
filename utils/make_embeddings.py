# DB 전체 임베딩 코드
# python make_embeddings.py

import os
import numpy as np
import psycopg
from FlagEmbedding import FlagAutoModel

from django.conf import settings

# ======================
# CONFIG
# ======================
DB_DSN = settings.DB_DSN

TABLES = [
    "actors",
    "agents",
    "behaviors",
    "conditions",
    "positions",
    "speeds",
]

ID_COL = "id"
DESC_COL = "description"
EMB_COL = "embedding"

BATCH_SIZE = 256
MODEL_NAME = "BAAI/bge-m3"
NORMALIZE = True

# ======================
# UTILS
# ======================
def to_numpy(x):
    if hasattr(x, "detach"):
        return x.detach().cpu().numpy()
    return np.asarray(x)

def l2_normalize(mat, eps=1e-12):
    n = np.linalg.norm(mat, axis=1, keepdims=True)
    return mat / (n + eps)

def encode_dense(model, texts):
    out = model.encode(texts)
    vecs = out["dense_vecs"] if isinstance(out, dict) else out
    vecs = to_numpy(vecs).astype(np.float32)
    if NORMALIZE:
        vecs = l2_normalize(vecs)
    return vecs

def vec_to_pgvector(v: np.ndarray) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in v.tolist()) + "]"

# ======================
# MAIN
# ======================
def main():
    print(f"Loading model: {MODEL_NAME}")
    model = FlagAutoModel.from_finetuned(MODEL_NAME, use_fp16=True)

    with psycopg.connect(DB_DSN) as conn:
        conn.autocommit = False

        for table in TABLES:
            print(f"\n=== Processing table: {table} ===")

            while True:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT {ID_COL}, {DESC_COL}
                        FROM public.{table}
                        WHERE {EMB_COL} IS NULL
                          AND {DESC_COL} IS NOT NULL
                        ORDER BY {ID_COL}
                        LIMIT %s
                        """,
                        (BATCH_SIZE,)
                    )
                    rows = cur.fetchall()

                if not rows:
                    print(f"✔ {table}: done")
                    break

                ids = [r[0] for r in rows]
                texts = [(r[1] or "").strip() for r in rows]

                # (선택) prefix – 검색 품질 안정
                texts = [f"DESC: {t}" for t in texts]

                vecs = encode_dense(model, texts)

                params = [
                    (vec_to_pgvector(vecs[i]), ids[i])
                    for i in range(len(ids))
                ]

                with conn.cursor() as cur:
                    cur.executemany(
                        f"""
                        UPDATE public.{table}
                        SET {EMB_COL} = %s::vector
                        WHERE {ID_COL} = %s
                        """,
                        params
                    )

                conn.commit()
                print(f"{table}: updated {len(ids)} rows (last id={ids[-1]})")

    print("\n🎉 All tables completed.")

if __name__ == "__main__":
    main()