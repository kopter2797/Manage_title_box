import pymysql

from config import DB_CONFIG


def inspect_table():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DESCRIBE users")
        columns = cursor.fetchall()
        print("Columns in 'users' table:")
        for col in columns:
            print(col)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_table()
