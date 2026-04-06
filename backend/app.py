from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import os
import hashlib
from dotenv import load_dotenv

from regras import processar_mensagem
from movidesk import enviar_resposta_movidesk
from ia import perguntar_ia_com_historico
from memoria import (
    obter_historico,
    salvar_mensagem,
    limpar_historico,
    fechar_redis,
)

# =========================
# LOAD ENV
# =========================
load_dotenv()

# =========================
# CONFIG DB
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
        port=DB_PORT,
    )


app = FastAPI()

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://10.20.30.23:3001",
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
    senha: str


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
# HELPERS
# =========================
def buscar_usuario_para_login(login: str):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT id, nome, login, password_hash, empresa, ativo
            FROM users
            WHERE login = %s
            """,
            (login,)
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def validar_chat_do_usuario(chat_id: int, user_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT id FROM chats WHERE id = %s AND user_id = %s",
            (chat_id, user_id)
        )
        chat = cur.fetchone()
        return bool(chat)
    finally:
        cur.close()
        conn.close()


def gerar_hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()


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
    login = dados.login.strip()
    senha = dados.senha.strip()

    if not login or not senha:
        raise HTTPException(status_code=400, detail="login e senha são obrigatórios")

    user = buscar_usuario_para_login(login)

    if not user:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    user_id, nome, user_login, password_hash, empresa, ativo = user

    if ativo is False:
        raise HTTPException(status_code=403, detail="Usuário inativo")

    if not password_hash:
        raise HTTPException(status_code=500, detail="Usuário sem senha configurada")

    senha_hash_input = gerar_hash_senha(senha)

    if senha_hash_input != password_hash:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    return {
        "id": user_id,
        "nome": nome,
        "login": user_login,
        "empresa": empresa,
    }


# =========================
# LISTAR CHATS DO USUÁRIO
# =========================
@app.get("/users/{user_id}/chats")
def listar_chats(user_id: int):
    conn = get_conn()
    cur = conn.cursor()

    try:
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

        return [
            {
                "id": c[0],
                "title": c[1],
                "created_at": str(c[2]),
            }
            for c in chats
        ]
    finally:
        cur.close()
        conn.close()


# =========================
# CRIAR CHAT
# =========================
@app.post("/chats")
def criar_chat(dados: CreateChatRequest):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT id FROM users WHERE id = %s AND ativo = TRUE",
            (dados.user_id,)
        )
        usuario = cur.fetchone()

        if not usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado ou inativo")

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

        return {"chat_id": chat_id}
    finally:
        cur.close()
        conn.close()


# =========================
# BUSCAR HISTÓRICO DO CHAT
# =========================
@app.get("/chats/{chat_id}/messages")
async def obter_mensagens(chat_id: int, user_id: int = Query(...)):
    if not validar_chat_do_usuario(chat_id, user_id):
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

    if not validar_chat_do_usuario(dados.chat_id, dados.user_id):
        raise HTTPException(status_code=403, detail="Chat inválido para este usuário")

    try:
        historico = await obter_historico(str(dados.chat_id), limite=20)

        resposta = perguntar_ia_com_historico(historico, mensagem)

        await salvar_mensagem(str(dados.chat_id), "user", mensagem)
        await salvar_mensagem(str(dados.chat_id), "assistant", resposta)

        historico_atualizado = await obter_historico(str(dados.chat_id), limite=50)

        return {
            "response": resposta,
            "history_length": len(historico_atualizado),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# RESETAR CHAT
# =========================
@app.post("/chat/reset")
async def reset_chat(dados: SessionRequest):
    if not validar_chat_do_usuario(dados.chat_id, dados.user_id):
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
