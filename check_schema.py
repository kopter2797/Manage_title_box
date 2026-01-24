import pymysql

from config import DB_CONFIG


def inspect_tables():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        tables = ['folder_rules', 'file_logs']
        
        for table in tables:
            print(f"\n--- Columns in '{table}' table ---")
            try:
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                for col in columns:
                    print(col)
            except Exception as e:
                print(f"Error describing {table}: {e}")
                
        conn.close()
    except Exception as e:
        print(f"Error connecting to DB: {e}")

if __name__ == "__main__":
    inspect_tables()
