import os
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
    )

    # Teste de conexão
    redis_client.ping()
    print("Redis conectado com sucesso")

except Exception as e:
    print(f"Erro ao conectar no Redis: {e}")
    redis_client = None
