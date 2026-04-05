from db import get_db_connection


def listar_chats_por_usuario(user_id: int):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT id, user_id, titulo, criado_em, atualizado_em
            FROM chats
            WHERE user_id = %s
            ORDER BY atualizado_em DESC, id DESC
            """,
            (user_id,)
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def criar_chat(user_id: int, titulo: str):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO chats (user_id, titulo)
            VALUES (%s, %s)
            RETURNING id, user_id, titulo, criado_em, atualizado_em
            """,
            (user_id, titulo)
        )
        chat = cur.fetchone()
        conn.commit()
        return chat
    finally:
        cur.close()
        conn.close()


def buscar_chat_por_id(chat_id: int):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT id, user_id, titulo, criado_em, atualizado_em
            FROM chats
            WHERE id = %s
            """,
            (chat_id,)
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()
