import os
import mysql.connector
from mysql.connector import pooling

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="sandbox_pool",
            pool_size=10,
            host=os.environ.get("DB_HOST", "127.0.0.1"),
            user=os.environ.get("DB_USER", "root"),
            password=os.environ.get("DB_PASSWORD", "1234"),
            database=os.environ.get("DB_NAME", "diffuserinter"),
            connection_timeout=3,
        )
    return _pool


def insert_into_mysql(browser_name, scenario_id, corpus, event_type, corpus_type, leak, violation, interaction=None):
    conn = None
    cursor = None
    try:
        conn = _get_pool().get_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO event_entry
            (browser_name, scenario_id, corpus, event_type, corpus_type, leak, violation, interaction)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (browser_name, scenario_id, corpus, event_type, corpus_type, leak, violation, interaction))
        conn.commit()
        return "good"
    except Exception as err:
        print(f"[DB Error] {err}")
        return "error"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
