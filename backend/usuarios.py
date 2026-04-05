from db import get_db_connection


def buscar_usuario_por_login(login: str):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT id, nome, login, empresa, criado_em
            FROM users
            WHERE login = %s
            """,
            (login,)
        )
        usuario = cur.fetchone()
        return usuario
    finally:
        cur.close()
        conn.close()
