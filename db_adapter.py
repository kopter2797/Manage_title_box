import pymysql
import os
from datetime import datetime

class DBAdapter:
    def __init__(self, app_config):
        self.mysql_config = app_config.get('DB_CONFIG')

    def get_user_by_id(self, user_id):
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                return user
            finally:
                conn.close()
        return None

    def get_user_by_username(self, username):
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                return user
            finally:
                conn.close()
        return None

    def create_user(self, username, email, password_hash):
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)", (username, email, password_hash))
                conn.commit()
                return True
            except Exception as e:
                print(e)
                return False
            finally:
                conn.close()
        return False

    def get_rules(self, user_id):
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT * FROM folder_rules WHERE is_active = 1 AND user_id = %s", (user_id,))
                return cursor.fetchall()
            finally:
                conn.close()
        return []

    def add_rule(self, user_id, category_name, target_folder, allowed_extensions):
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO folder_rules (category_name, target_folder_path, allowed_extensions, is_active, user_id) VALUES (%s, %s, %s, 1, %s)", 
                               (category_name, target_folder, allowed_extensions, user_id))
                conn.commit()
                return True
            finally:
                conn.close()
        return False

    def delete_rule(self, rule_id, user_id):
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE folder_rules SET is_active = 0 WHERE id = %s AND user_id = %s", (rule_id, user_id))
                conn.commit()
                return True
            finally:
                conn.close()
        return False

    def log_file_move(self, filename, extension, source, destination, size_kb, status, category_name, user_id):
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor()
                query = """
                    INSERT INTO file_logs (filename, extension, source_path, destination_path, file_size_kb, status, moved_at, category_name, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (filename, extension, source, destination, size_kb, status, datetime.now(), category_name, user_id)
                cursor.execute(query, values)
                conn.commit()
            finally:
                conn.close()

    def get_category_stats(self, user_id):
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                query = """
                    SELECT category_name, COUNT(*) as file_count 
                    FROM file_logs 
                    WHERE status = 'Success' AND user_id = %s
                    GROUP BY category_name
                """
                cursor.execute(query, (user_id,))
                return cursor.fetchall()
            finally:
                conn.close()
        return []

    def get_files(self, user_id, category_name=None, query=None):
        files = []
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                sql = "SELECT * FROM file_logs WHERE user_id = %s AND status = 'Success'"
                params = [user_id]
                
                if category_name:
                    sql += " AND category_name = %s"
                    params.append(category_name)
                
                sql += " ORDER BY moved_at DESC"
                
                cursor.execute(sql, tuple(params))
                files = cursor.fetchall()
            finally:
                conn.close()
        return files

    def get_file_by_id(self, log_id, user_id):
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT * FROM file_logs WHERE id = %s AND user_id = %s", (log_id, user_id))
                return cursor.fetchone()
            finally:
                conn.close()
        return None

    def delete_file_log(self, log_id):
         conn = self._get_mysql_conn()
         if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM file_logs WHERE id = %s", (log_id,))
                conn.commit()
                return True
            finally:
                conn.close()
         return False
    
    def update_file_path(self, log_id, new_name, new_path):
        conn = self._get_mysql_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE file_logs SET filename = %s, destination_path = %s WHERE id = %s", (new_name, new_path, log_id))
                conn.commit()
                return True
            finally:
                conn.close()
        return False

    def _get_mysql_conn(self):
        try:
            return pymysql.connect(**self.mysql_config)
        except Exception as e:
            print(f"MySQL Connection Error: {e}")
            return None
