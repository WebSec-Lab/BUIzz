import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234"
)

cursor = conn.cursor()

cursor.execute("CREATE DATABASE IF NOT EXISTS diffuserinter;")
cursor.execute("USE diffuserinter;")

create_table_sql = """
CREATE TABLE IF NOT EXISTS event_entry (
    id INT PRIMARY KEY AUTO_INCREMENT,
    browser_name VARCHAR(50),
    scenario_id VARCHAR(500),
    corpus VARCHAR(500),
    event_type ENUM('interaction', 'corpus'),
    corpus_type ENUM('csp', 'samesite', 'sandbox', 'coop', 'permission-policy', 'referrer-policy', 'hsts', 'x-frame-options'),
    leak VARCHAR(500),
    violation VARCHAR(500),
    interaction VARCHAR(255) NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

cursor.execute(create_table_sql)

print("Database 'diffuserinter' and table 'event_entry' created successfully!")

cursor.close()
conn.close()
