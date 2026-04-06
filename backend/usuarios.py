from db import get_db_connection


def autenticar_usuario(login: str, senha: str):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT id, nome, login, empresa
            FROM users
            WHERE login = %s AND senha = %s
            """,
            (login, senha)
        )
        usuario = cur.fetchone()
        return usuario
    finally:
        cur.close()
        conn.close()
