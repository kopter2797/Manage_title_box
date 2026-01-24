import pymysql

from config import DB_CONFIG


def update_database():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Add user_id to folder_rules
        try:
            print("Adding user_id to folder_rules...")
            cursor.execute("ALTER TABLE folder_rules ADD COLUMN user_id INT(11)")
            print("Success!")
        except pymysql.MySQLError as e:
            print(f"Skipped (might already exist): {e}")

        # Add user_id to file_logs
        try:
            print("Adding user_id to file_logs...")
            cursor.execute("ALTER TABLE file_logs ADD COLUMN user_id INT(11)")
            print("Success!")
        except pymysql.MySQLError as e:
            print(f"Skipped (might already exist): {e}")

        conn.commit()
        conn.close()
        print("\nDatabase update completed.")
    except Exception as e:
        print(f"Error connecting to DB: {e}")

if __name__ == "__main__":
    update_database()
