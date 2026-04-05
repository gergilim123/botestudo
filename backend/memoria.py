import json
from datetime import datetime, timezone

import redis.asyncio as redis

REDIS_URL = "redis://localhost:6379/0"
TTL_SECONDS = 60 * 60 * 24  # 24 horas
MAX_MESSAGES = 50

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def _chat_key(chat_id: str) -> str:
    return f"chat:{chat_id}:messages"


async def salvar_mensagem(chat_id: str, role: str, content: str) -> None:
    key = _chat_key(chat_id)

    mensagem = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    await redis_client.rpush(key, json.dumps(mensagem, ensure_ascii=False))
    await redis_client.ltrim(key, -MAX_MESSAGES, -1)
    await redis_client.expire(key, TTL_SECONDS)


async def obter_historico(chat_id: str, limite: int = 20) -> list[dict]:
    key = _chat_key(chat_id)
    itens = await redis_client.lrange(key, -limite, -1)
    return [json.loads(item) for item in itens]


async def limpar_historico(chat_id: str) -> None:
    key = _chat_key(chat_id)
    await redis_client.delete(key)


async def fechar_redis() -> None:
    await redis_client.aclose()
