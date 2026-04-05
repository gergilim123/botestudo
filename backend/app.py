from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import os
from dotenv import load_dotenv

from regras import processar_mensagem
from movidesk import enviar_resposta_movidesk
from ia import perguntar_ia_com_historico
from memoria import (
    obter_historico,
    salvar_mensagem,
    limpar_historico,
    fechar_redis
)

# =========================
# LOAD ENV
# =========================
load_dotenv()

# =========================
# CONFIG DB (PADRÃO .env)
# =========================
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DB_NAME = os.getenv("POSTGRES_DB", "bot_movidesk")
DB_USER = os.getenv("POSTGRES_USER", "botuser")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "botpass123")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )


app = FastAPI()

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://10.20.30.19:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# MODELS
# =========================
class LoginRequest(BaseModel):
    login: str


class CreateChatRequest(BaseModel):
    user_id: int


class ChatMessageRequest(BaseModel):
    user_id: int
    chat_id: int
    message: str


class SessionRequest(BaseModel):
    chat_id: int
    user_id: int


class MensagemMovidesk(BaseModel):
    cliente: str
    mensagem: str
    ticket_id: int


# =========================
# STATUS
# =========================
@app.get("/")
def status():
    return {"status": "Bot Movidesk online"}


# =========================
# AUTH
# =========================
@app.post("/auth/login")
def login(dados: LoginRequest):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, nome, login, empresa FROM users WHERE login = %s",
        (dados.login,)
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return {
        "id": user[0],
        "nome": user[1],
        "login": user[2],
        "empresa": user[3],
    }


# =========================
# LISTAR CHATS DO USUÁRIO
# =========================
@app.get("/users/{user_id}/chats")
def listar_chats(user_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, titulo, criado_em
        FROM chats
        WHERE user_id = %s
        ORDER BY criado_em DESC
        """,
        (user_id,)
    )

    chats = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "id": c[0],
            "title": c[1],
            "created_at": str(c[2]),
        }
        for c in chats
    ]


# =========================
# CRIAR CHAT
# =========================
@app.post("/chats")
def criar_chat(dados: CreateChatRequest):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO chats (user_id, titulo)
        VALUES (%s, 'Novo chat')
        RETURNING id
        """,
        (dados.user_id,)
    )

    chat_id = cur.fetchone()[0]
    conn.commit()

    cur.close()
    conn.close()

    return {"chat_id": chat_id}


# =========================
# BUSCAR HISTÓRICO DO CHAT
# =========================
@app.get("/chats/{chat_id}/messages")
async def obter_mensagens(chat_id: int, user_id: int = Query(...)):
    conn = get_conn()
    cur = conn.cursor()

    # valida dono
    cur.execute(
        "SELECT id FROM chats WHERE id = %s AND user_id = %s",
        (chat_id, user_id)
    )

    chat = cur.fetchone()

    cur.close()
    conn.close()

    if not chat:
        raise HTTPException(status_code=403, detail="Chat não pertence ao usuário")

    historico = await obter_historico(str(chat_id), limite=50)

    return {"messages": historico}


# =========================
# ENVIAR MENSAGEM
# =========================
@app.post("/chat")
async def chat(dados: ChatMessageRequest):
    mensagem = dados.message.strip()

    if not mensagem:
        raise HTTPException(status_code=400, detail="message é obrigatório")

    conn = get_conn()
    cur = conn.cursor()

    # valida dono
    cur.execute(
        "SELECT id FROM chats WHERE id = %s AND user_id = %s",
        (dados.chat_id, dados.user_id)
    )

    chat = cur.fetchone()

    cur.close()
    conn.close()

    if not chat:
        raise HTTPException(status_code=403, detail="Chat inválido para este usuário")

    try:
        historico = await obter_historico(str(dados.chat_id), limite=20)

        resposta = perguntar_ia_com_historico(historico, mensagem)

        await salvar_mensagem(str(dados.chat_id), "user", mensagem)
        await salvar_mensagem(str(dados.chat_id), "assistant", resposta)

        historico_atualizado = await obter_historico(str(dados.chat_id), limite=50)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "response": resposta,
        "history_length": len(historico_atualizado),
    }


# =========================
# RESETAR CHAT
# =========================
@app.post("/chat/reset")
async def reset_chat(dados: SessionRequest):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM chats WHERE id = %s AND user_id = %s",
        (dados.chat_id, dados.user_id)
    )

    chat = cur.fetchone()

    cur.close()
    conn.close()

    if not chat:
        raise HTTPException(status_code=403, detail="Chat inválido")

    await limpar_historico(str(dados.chat_id))

    return {"status": "ok"}


# =========================
# MOVEDESK
# =========================
@app.post("/webhook-movidesk")
def receber_mensagem(dados: MensagemMovidesk):
    resposta = processar_mensagem(dados.cliente, dados.mensagem)
    enviar_resposta_movidesk(dados.ticket_id, resposta)

    return {"status": "ok"}


# =========================
# SHUTDOWN
# =========================
@app.on_event("shutdown")
async def shutdown_event():
    await fechar_redis() 
