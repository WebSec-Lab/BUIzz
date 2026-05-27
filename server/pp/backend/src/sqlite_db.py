import sqlite3
DB_NAME = 'pp_violation.db'


def save_pp_in_sqlite(query, browser, scenario, bf):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            sql_insert = """
                INSERT INTO pp (query, browser, scenario, bf)
                VALUES (?, ?, ?, ?);
            """
            cursor.execute(sql_insert, (query, browser, scenario, bf))
            conn.commit()
            return "True"

    except sqlite3.Error as e:
        return f"False {e}"