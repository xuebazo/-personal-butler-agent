"""
共享基础设施：配置加载、ChromaDB 客户端、本地 embedding 模型
被 ingest.py / query.py / butler.py 引用
"""

import os
import re
import yaml
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CONFIG_PATH = Path.home() / ".butler" / "config.yaml"

# ── 配置加载（支持 ${ENV_VAR} 占位符）──────────────────────

def _resolve_env(value: str) -> str:
    """解析 ${VAR} 格式的环境变量占位符"""
    if isinstance(value, str):
        pattern = re.compile(r'\$\{(\w+)\}')
        for match in pattern.findall(value):
            env_val = os.getenv(match, "")
            if not env_val:
                print(f"WARNING: env var {match} is not set")
            value = value.replace(f"${{{match}}}", env_val)
    return value


def _walk_resolve(obj):
    """递归解析配置树中所有的环境变量"""
    if isinstance(obj, dict):
        return {k: _walk_resolve(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_walk_resolve(v) for v in obj]
    elif isinstance(obj, str):
        return _resolve_env(obj)
    return obj


if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"找不到配置文件: {CONFIG_PATH}")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _raw = yaml.safe_load(f)
config = _walk_resolve(_raw)

# ── ChromaDB 客户端 ─────────────────────────────────────────

db_client = chromadb.PersistentClient(
    path=str(Path(config["paths"]["vectordb"]).expanduser())
)
collection = db_client.get_or_create_collection(
    name="personal_context",
    metadata={"hnsw:space": "cosine"}
)

def get_learning_collection() -> chromadb.Collection:
    """返回学习材料专用 collection，与 personal_context 物理隔离"""
    collection_name = config.get("learning", {}).get("collection_name", "learning_materials")
    return db_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


# ── 本地 embedding 模型（懒加载）────────────────────────────

_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        model_name = config["models"]["embedding"]
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


def get_embedding(text: str) -> list[float]:
    model = get_embedding_model()
    return model.encode(text).tolist()
