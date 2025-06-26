import sqlite3
import json

conn = sqlite3.connect('sn90.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Data_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        statement TEXT NOT NULL,
        response TEXT NOT NULL
    )
''')

def insert_data(statement, response_dict):
    res = get_response(statement)
    if (res != None and response_dict['confidence'] <= res['confidence']):
        return
    response_json = json.dumps(response_dict)
    cursor.execute('''
        INSERT INTO Data_table (statement, response) VALUES (?, ?)
    ''', (statement, response_json))
    conn.commit()

def get_response(statement):
    cursor.execute('SELECT response FROM Data_table WHERE LOWER(statement) = LOWER(?)', (statement,))
    row = cursor.fetchone()
    if row:
        response_json = row[0]
        return json.loads(response_json)
    else:
        return None

# Example usage
# insert_data("Hello", {"reply": "Hi there!", "emotion": "happy", "confidence": 90})
# insert_data("What's your name?", {"reply": "I'm ChatGPT.", "emotion": "neutral", "confidence": 80})
# ret = get_response("What's your name?")
# print(ret)