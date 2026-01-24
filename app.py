import os
import shutil
import pymysql
import zipfile
import io
import stat
import time
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import difflib
import os
try:
    from config import DB_CONFIG, SECRET_KEY
except ImportError:
    # Fallback for Production / Env Vars
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST'),
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'database': os.environ.get('DB_NAME'),
        'port': int(os.environ.get('DB_PORT', 3306))
    }
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')

from db_adapter import DBAdapter

# Initialize DB Adapter
app_config = {
    'DB_CONFIG': DB_CONFIG
}

db = DBAdapter(app_config)


import sys

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

app.secret_key = SECRET_KEY  # Needed for flash messages

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Configuration is now in config.py


class User(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = str(id) # Ensure ID is always a string for compatibility
        self.username = username
        self.email = email
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        user_data = db.get_user_by_id(user_id)
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['email'], user_data['password_hash'])
        return None

    @staticmethod
    def get_by_username(username):
        user_data = db.get_user_by_username(username)
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['email'], user_data['password_hash'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def get_category_stats(user_id):
    return db.get_category_stats(user_id)

def log_file_move(filename, extension, source, destination, size_kb, status, category_name, user_id):
    db.log_file_move(filename, extension, source, destination, size_kb, status, category_name, user_id)

def force_delete(file_path):
    """
    Attempts to delete a file, clearing read-only attribute if necessary.
    Retries up to 3 times to handle temporary locks.
    """
    if not os.path.exists(file_path):
        return True

    for i in range(3):
        try:
            os.remove(file_path)
            return True
        except PermissionError:
            # Clear Read-Only attribute
            try:
                os.chmod(file_path, stat.S_IWRITE)
                os.remove(file_path)
                return True
            except Exception:
                pass
        except OSError:
            pass
        
        # Wait briefly before retry
        time.sleep(0.1)
    
    return False

def process_file_move(source_path, rules, user_id):
    """
    Helper function to process a single file against a list of rules.
    Uses aggressive copy-then-delete logic to ensure source removal.
    """
    filename = os.path.basename(source_path)
    if os.path.isdir(source_path):
        return False, "Is a directory", None

    file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
    file_size_kb = os.path.getsize(source_path) / 1024

    for rule in rules:
        allowed_exts = [e.strip().lower() for e in rule['allowed_extensions'].split(',')]
        
        if file_ext in allowed_exts:
            target_base_path = rule['target_folder_path']
            category_name = rule['category_name']
            
            # Create category subfolder: Target_Base_Path / Category_Name
            target_folder = os.path.join(target_base_path, category_name)
            
            # Create target folder if it doesn't exist
            if not os.path.exists(target_folder):
                try:
                    os.makedirs(target_folder)
                except OSError as e:
                    log_file_move(filename, file_ext, source_path, target_folder, file_size_kb, f"Error creating folder: {e}", category_name, user_id)
                    return False, f"Error creating folder: {e}", None

            destination_path = os.path.join(target_folder, filename)
            
            # Handle duplicate filenames
            if os.path.exists(destination_path):
                base, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                new_filename = f"{base}_{timestamp}{ext}"
                destination_path = os.path.join(target_folder, new_filename)

            try:
                print(f"DEBUG: Operation Start: {source_path} -> {destination_path}")
                
                # 1. Copy2 (Preserves metadata)
                shutil.copy2(source_path, destination_path)
                
                # 2. Verify Destination
                if not os.path.exists(destination_path) or os.path.getsize(destination_path) == 0:
                     raise Exception("Copy failed: Destination missing or empty")

                # 3. Aggressive Delete Source
                delete_success = False
                delete_error = None
                
                # Attempt 1: Standard remove
                try:
                    os.remove(source_path)
                    delete_success = True
                except Exception as e:
                    delete_error = e
                    # Attempt 2: Clear Read-Only and remove
                    try:
                        os.chmod(source_path, stat.S_IWRITE)
                        os.remove(source_path)
                        delete_success = True
                    except Exception as e2:
                        delete_error = e2
                        # Attempt 3: Windows Shell Force Delete
                        try:
                            # Use quotes to handle spaces in path
                            cmd = f'del /f /q "{source_path}"'
                            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            
                            # Check if really gone
                            if not os.path.exists(source_path):
                                delete_success = True
                            else:
                                delete_error = "Shell delete command completed but file remains"
                        except Exception as e3:
                             delete_error = f"All delete methods failed. Last error: {e3}"

                if delete_success:
                    log_file_move(filename, file_ext, source_path, destination_path, file_size_kb, "Success", category_name, user_id)
                    return True, "Success", category_name
                else:
                    msg = f"Warning: File copied but NOT deleted. {delete_error}"
                    print(f"DEBUG: {msg}")
                    log_file_move(filename, file_ext, source_path, destination_path, file_size_kb, msg, category_name, user_id)
                    return False, msg, None

            except Exception as e:
                print(f"DEBUG: Critical Error moving file: {e}")
                log_file_move(filename, file_ext, source_path, target_folder, file_size_kb, f"Error: {e}", category_name, user_id)
                return False, f"Error: {e}", None
    
    return False, "No matching rule", None

def organize_files(source_folder):
    if not os.path.exists(source_folder):
        print(f"DEBUG: Source folder not found: {source_folder}")
        return 0, 0

    rules = db.get_rules(current_user.id)
    if not rules:
        print("DEBUG: No rules found")
        return 0, 0

    moved_count = 0
    errors_count = 0
    
    # "Remove Path System" - Just listing files directly for Method 1
    print(f"DEBUG: Listing files in: {source_folder}")
    try:
        for filename in os.listdir(source_folder):
            source_path = os.path.join(source_folder, filename)
            
            # "Take only files in the folder"
            if not os.path.isfile(source_path):
                continue
                
            # Execute Move logic
            moved, msg, cat = process_file_move(source_path, rules, current_user.id)
            
            if moved:
                moved_count += 1
                print(f"DEBUG: Moved {filename}")
            elif "Error" in msg:
                errors_count += 1
                print(f"DEBUG: Error processing {filename}: {msg}")

    except Exception as e:
        print(f"DEBUG: Error listing folder: {e}")
        return 0, 1

    return moved_count, errors_count

@app.route('/')
@login_required
def index():
    categories = get_category_stats(current_user.id)
    return render_template('index.html', categories=categories)

@app.route('/search')
@login_required
def search_files():
    query = request.args.get('q', '').lower()
    files = []
    
    if query:
        # Fetch directly using adapter which abstracts the DB nature
        # Note: Optimization could be done to filter by query at DB level if desired, 
        # but existing logic relies on Python-based fuzzy matching.
        all_files = db.get_files(current_user.id, query=None)
        
        results = []
        for file in all_files:
            fname = file['filename'].lower()
            
            # 1. Exact Substring Match (Highest Priority)
            if query in fname:
                file['match_score'] = 1.0 + (len(query) / len(fname)) # Boost by coverage
                results.append(file)
                continue
                
            # 2. Fuzzy Match (Lower Priority)
            # Use quick ratio for performance, checks for similarity
            ratio = difflib.SequenceMatcher(None, query, fname).quick_ratio()
            if ratio > 0.5: # Threshold for "similarity"
                file['match_score'] = ratio
                results.append(file)
        
        # Sort logic
        sort_by = request.args.get('sort', 'relevance')
        
        if sort_by == 'date_desc':
            files = sorted(results, key=lambda x: x['moved_at'], reverse=True)
        elif sort_by == 'date_asc':
            files = sorted(results, key=lambda x: x['moved_at'], reverse=False)
        elif sort_by == 'size_desc':
            files = sorted(results, key=lambda x: x['file_size_kb'], reverse=True)
        elif sort_by == 'size_asc':
            files = sorted(results, key=lambda x: x['file_size_kb'], reverse=False)
        elif sort_by == 'name_asc':
            files = sorted(results, key=lambda x: x['filename'].lower(), reverse=False)
        elif sort_by == 'name_desc':
            files = sorted(results, key=lambda x: x['filename'].lower(), reverse=True)
        else:
            # Default: specific relevance sort
            files = sorted(results, key=lambda x: x['match_score'], reverse=True)
    
    return render_template('search_results.html', files=files, query=query, current_sort=request.args.get('sort', 'relevance'))

@app.route('/api/search_suggestions')
@login_required
def search_suggestions():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
        
    all_files = db.get_files(current_user.id)
    
    matches = []
    for file in all_files:
        fname = file['filename']
        fname_lower = fname.lower()
        
        # 1. Exact Substring
        if query in fname_lower:
            matches.append({'value': fname, 'score': 1.0 + (len(query) / len(fname))})
            continue
            
        # 2. Fuzzy Match
        ratio = difflib.SequenceMatcher(None, query, fname_lower).quick_ratio()
        if ratio > 0.5:
            matches.append({'value': fname, 'score': ratio})
    
    # Sort and take top 5
    matches = sorted(matches, key=lambda x: x['score'], reverse=True)[:5]
    suggestions = [m['value'] for m in matches]
        
    return jsonify(suggestions)

@app.route('/category/<category_name>')
@login_required
def category_view(category_name):
    sort_by = request.args.get('sort', 'date_desc')
    
    order_clause = "ORDER BY moved_at DESC"
    if sort_by == 'date_asc':
        order_clause = "ORDER BY moved_at ASC"
    elif sort_by == 'size_desc':
        order_clause = "ORDER BY file_size_kb DESC"
    elif sort_by == 'size_asc':
        order_clause = "ORDER BY file_size_kb ASC"
    elif sort_by == 'name_asc':
        order_clause = "ORDER BY filename ASC"
    elif sort_by == 'name_desc':
        order_clause = "ORDER BY filename DESC"
        
    files = db.get_files(current_user.id, category_name=category_name)
    
    # Sorting logic needs to apply here as get_files returns iterator/list depending on DB
    if sort_by == 'date_desc':
        files = sorted(files, key=lambda x: x['moved_at'], reverse=True)
    elif sort_by == 'date_asc':
        files = sorted(files, key=lambda x: x['moved_at'], reverse=False)
    elif sort_by == 'size_desc':
        files = sorted(files, key=lambda x: x['file_size_kb'], reverse=True)
    elif sort_by == 'size_asc':
        files = sorted(files, key=lambda x: x['file_size_kb'], reverse=False)
    elif sort_by == 'name_asc':
        files = sorted(files, key=lambda x: x['filename'].lower(), reverse=False)
    elif sort_by == 'name_desc':
        files = sorted(files, key=lambda x: x['filename'].lower(), reverse=True)
    return render_template('category_view.html', files=files, category_name=category_name, current_sort=sort_by)

@app.route('/open_file', methods=['POST'])
@login_required
def open_file():
    file_path = request.form.get('file_path')
    if file_path and os.path.exists(file_path):
        try:
            os.startfile(file_path) # Windows only
            flash(f'กำลังเปิด {file_path}', 'success')
        except Exception as e:
            flash(f'เกิดข้อผิดพลาดในการเปิดไฟล์: {e}', 'danger')
    else:
        flash('ไม่พบไฟล์', 'danger')
    
    # Redirect back to the previous page
    return redirect(request.referrer or url_for('index'))

@app.route('/download/<log_id>')
@login_required
def download_file(log_id):
    file_record = db.get_file_by_id(log_id, current_user.id)
    if not file_record:
        flash('ไม่พบข้อมูลไฟล์', 'danger')
        return redirect(request.referrer or url_for('index'))

    file_path = file_record['destination_path']
    filename = file_record['filename']

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        flash('ไม่พบไฟล์บนดิสก์', 'danger')
        return redirect(request.referrer or url_for('index'))

@app.route('/delete_file/<log_id>', methods=['POST'])
@login_required
def delete_file(log_id):
    try:
        file_record = db.get_file_by_id(log_id, current_user.id)
        if not file_record:
            return jsonify({'success': False, 'message': 'ไม่พบข้อมูลไฟล์'}), 404

        file_path = file_record['destination_path']

        # Delete from Disk
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาดในการลบไฟล์จากดิสก์: {e}'}), 500
        
        # Delete from DB
        if db.delete_file_log(log_id):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาดในการลบข้อมูลจากฐานข้อมูล'}), 500

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/rename_file', methods=['POST'])
@login_required
def rename_file():
    log_id = request.form.get('log_id')
    new_name = request.form.get('new_name')
    
    if not log_id or not new_name:
        return jsonify({'success': False, 'message': 'ข้อมูลไม่ครบถ้วน'}), 400
    
    # Validate filename - Check for invalid Windows characters
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        if char in new_name:
            return jsonify({'success': False, 'message': f'ชื่อไฟล์ไม่สามารถมีตัวอักษรพิเศษ: {char}'}), 400
        
    try:
        file_record = db.get_file_by_id(log_id, current_user.id)
        
        if not file_record:
            return jsonify({'success': False, 'message': 'ไม่พบข้อมูลไฟล์'}), 404
            
        old_path = file_record['destination_path']
        directory = os.path.dirname(old_path)
        
        # Validate extension
        name_parts = os.path.splitext(new_name)
        new_filename_base = name_parts[0]
        new_extension = name_parts[1]
        
        # If user didn't provide extension, append original extension
        if not new_extension:
            new_extension = '.' + file_record['extension'] if not file_record['extension'].startswith('.') else file_record['extension']
            new_name = new_filename_base + new_extension
        
        new_path = os.path.join(directory, new_name)
        
        # Check if new name already exists
        if os.path.exists(new_path):
             return jsonify({'success': False, 'message': 'ชื่อไฟล์นี้มีอยู่แล้ว'}), 400
             
        # Check if old file exists
        if not os.path.exists(old_path):
            return jsonify({'success': False, 'message': 'ไม่พบไฟล์ต้นฉบับบนดิสก์'}), 404
        
        # Try to rename the file
        try:
            # Check if file is read-only
            if os.access(old_path, os.W_OK) == False:
                # Try to remove read-only attribute
                try:
                    os.chmod(old_path, stat.S_IWRITE)
                except:
                    return jsonify({'success': False, 'message': 'ไฟล์เป็น Read-Only และไม่สามารถปลดล็อคได้'}), 500
            
            os.rename(old_path, new_path)
            
        except PermissionError as e:
            return jsonify({'success': False, 'message': 'ไม่มีสิทธิ์เปลี่ยนชื่อไฟล์ (ไฟล์อาจกำลังเปิดอยู่)'}), 500
        except OSError as e:
            error_msg = str(e)
            if 'being used by another process' in error_msg or 'WinError 32' in error_msg:
                return jsonify({'success': False, 'message': 'ไฟล์กำลังถูกใช้งานโดยโปรแกรมอื่น กรุณาปิดไฟล์ก่อน'}), 500
            else:
                return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาดในการเปลี่ยนชื่อ: {error_msg}'}), 500
             
        # Update DB
        if db.update_file_path(log_id, new_name, new_path):
             return jsonify({'success': True, 'new_name': new_name})
        else:
             # Rollback - rename back to original
             try:
                 os.rename(new_path, old_path)
             except:
                 pass
             return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาดในการอัพเดทฐานข้อมูล'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'ข้อผิดพลาดที่ไม่คาดคิด: {str(e)}'}), 500


@app.route('/get_common_folder', methods=['GET'])
@login_required
def get_common_folder():
    """Get path to common folders like Downloads, Desktop, Documents"""
    folder_type = request.args.get('type', 'downloads')
    
    try:
        # Get user's home directory
        home = os.path.expanduser('~')
        
        folders = {
            'downloads': os.path.join(home, 'Downloads'),
            'desktop': os.path.join(home, 'Desktop'),
            'documents': os.path.join(home, 'Documents'),
            'pictures': os.path.join(home, 'Pictures'),
            'videos': os.path.join(home, 'Videos'),
            'music': os.path.join(home, 'Music'),
        }
        
        # For Windows with OneDrive, check alternate paths
        if os.name == 'nt':
            onedrive_path = os.path.join(home, 'OneDrive')
            if os.path.exists(onedrive_path):
                onedrive_folders = {
                    'desktop': os.path.join(onedrive_path, 'Desktop'),
                    'documents': os.path.join(onedrive_path, 'Documents'),
                    'pictures': os.path.join(onedrive_path, 'Pictures'),
                }
                # Use OneDrive paths if they exist
                for key, path in onedrive_folders.items():
                    if os.path.exists(path):
                        folders[key] = path
        
        if folder_type in folders:
            path = folders[folder_type]
            exists = os.path.exists(path)
            return jsonify({
                'success': True, 
                'path': path,
                'exists': exists
            })
        else:
            return jsonify({'success': False, 'message': 'Unknown folder type'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/run', methods=['POST'])
@login_required
def run_organizer():
    # Helper to check if it's a JSON request
    is_json = request.is_json or request.content_type == 'application/json'
    
    source_paths = []
    
    if is_json:
        data = request.get_json()
        # Support both 'source_path' (single) and 'source_paths' (list)
        if 'source_paths' in data and isinstance(data['source_paths'], list):
            source_paths = data['source_paths']
        elif 'source_path' in data:
             source_paths.append(data['source_path'])
    else:
        # Form submit fallback
        sp = request.form.get('source_path')
        if sp:
            source_paths.append(sp)
        
    if not source_paths:
        message = 'กรุณาระบุที่อยู่โฟลเดอร์ต้นทางอย่างน้อย 1 โฟลเดอร์'
        if is_json:
             return jsonify({'success': False, 'message': message})
        flash(message, 'danger')
        return redirect(url_for('index'))

    total_moved = 0
    total_errors = 0
    processed_folders = 0
    not_found_paths = []
    
    print(f"DEBUG /run: Received {len(source_paths)} paths: {source_paths}")
    
    for path in source_paths:
        path = path.strip()
        if not path: continue
        
        print(f"DEBUG /run: Processing path: {path}")
        
        # Check specific folder existence
        if not os.path.exists(path):
            print(f"DEBUG /run: Path NOT FOUND: {path}")
            not_found_paths.append(path)
            continue
        
        print(f"DEBUG /run: Path EXISTS, calling organize_files()")
        moved, errors = organize_files(path)
        # organize_files defined to return ints now: (moved_count, errors_count)
        # Note: organize_files returns (False, msg) in some early checks, we need to handle that.
        # Wait, I refactored the *end* of organize_files, but the *beginning* still returns (False, msg).
        # I need to fix organize_files fully or handle mixed return types here.
        # Let's assume I fix organize_files to ALWAYS return (moved, errors) or raise exception.
        # CHECK: organize_files returns (False, "err") on fail.
        
        if isinstance(moved, bool) and moved is False:
             # It failed early (e.g. folder not found)
             print(f"DEBUG /run: organize_files returned False for {path}")
             continue
             
        total_moved += moved
        total_errors += errors
        processed_folders += 1
        print(f"DEBUG /run: Moved {moved} files from {path}")

    message = f"ดำเนินการเสร็จสิ้น {processed_folders} โฟลเดอร์. ย้ายไฟล์รวม: {total_moved}, ผิดพลาด: {total_errors}"
    success = True # Consider it a success if we ran without crashing, or check if processed_folders > 0
    
    if not_found_paths:
        message += f" | ไม่พบโฟลเดอร์: {', '.join(not_found_paths[:3])}"
        if len(not_found_paths) > 3:
            message += f" และอีก {len(not_found_paths) - 3} โฟลเดอร์"
    
    if processed_folders == 0 and len(source_paths) > 0:
        success = False
        if not_found_paths:
            message = f"ไม่พบโฟลเดอร์ต้นทาง: {', '.join(not_found_paths[:3])}"
        else:
            message = "ไม่พบโฟลเดอร์ต้นทาง หรือเกิดข้อผิดพลาดในการตรวจสอบกฎ"

    if is_json:
        # Fetch updated stats
        stats = get_category_stats(current_user.id)
        return jsonify({
            'success': success, 
            'message': message,
            'stats': stats
        })
        
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('index'))

@app.route('/upload_files', methods=['POST'])
@login_required
def upload_files():
    uploaded_files = request.files.getlist('files')
    if not uploaded_files:
        return jsonify({'success': False, 'message': 'ไม่พบไฟล์ที่อัพโหลด'}), 400
    
    rules = db.get_rules(current_user.id)
    if not rules:
        return jsonify({'success': False, 'message': 'ไม่พบกฎการจัดระเบียบ'}), 400

    temp_dir = os.path.join(os.getcwd(), 'temp_uploads')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    processed_count = 0
    errors_count = 0
    
    for file in uploaded_files:
        if file.filename == '':
            continue
            
        # Custom Safe Filename to support Thai and Spaces
        import re
        def safe_filename(name):
            # 1. Get just the basename (security)
            name = os.path.basename(name)
            
            # 2. Split extension
            base, ext = os.path.splitext(name)
            
            # 3. Allow Thai (\u0E00-\u0E7F), Alphanumeric, Spaces, Dashes, Underscores
            # Remove anything else
            # Note: \w matches [a-zA-Z0-9_] (and potentially others depending on locale, but specific range is safer)
            # Regex: Keep [a-zA-Z0-9_ -] and Thai range
            safe_base = re.sub(r'[^\w\s\-\(\)\.\u0E00-\u0E7F]', '', base)
            
            # 4. Collapse multiple spaces
            safe_base = re.sub(r'\s+', ' ', safe_base).strip()
            
            # 5. Fallback if empty
            if not safe_base:
                safe_base = "unnamed_file"
                
            return safe_base + ext

        filename = safe_filename(file.filename)
        temp_path = os.path.join(temp_dir, filename)
        
        try:
            file.save(temp_path)
            moved, msg, cat = process_file_move(temp_path, rules, current_user.id)
            if moved:
                processed_count += 1
            else:
                 # Clean up if not moved (not matched or error)
                 if os.path.exists(temp_path):
                     try: os.remove(temp_path) 
                     except: pass
                 if "Error" in msg:
                     errors_count += 1
        except Exception as e:
            errors_count += 1
            # ensure cleanup
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
    
    stats = get_category_stats(current_user.id)
    return jsonify({
        'success': True, 
        'message': f'จัดระเบียบสำเร็จ {processed_count} ไฟล์. ผิดพลาด: {errors_count}', 
        'stats': stats
    })

@app.route('/scan_files', methods=['GET'])
@login_required
def scan_files():
    path = request.args.get('path')
    if not path or not os.path.exists(path):
        return jsonify({'success': False, 'message': 'ไม่พบที่อยู่โฟลเดอร์'}), 400
        
    files_found = []
    rules = db.get_rules(current_user.id)
    
    try:
        # Limit to 500 files to prevent browser crash
        count = 0
        with os.scandir(path) as it:
            for entry in it:
                if count > 500:
                    break
                if entry.is_file():
                    # Check if it matches any rule
                    file_ext = entry.name.split('.')[-1].lower() if '.' in entry.name else ''
                    category_match = None
                    
                    for rule in rules:
                        allowed_exts = [e.strip().lower() for e in rule['allowed_extensions'].split(',')]
                        if file_ext in allowed_exts:
                            category_match = rule['category_name']
                            break
                    
                    files_found.append({
                        'name': entry.name,
                        'path': entry.path,
                        'size': entry.stat().st_size,
                        'category': category_match
                    })
                    count += 1
                
        return jsonify({'success': True, 'files': files_found})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/process_scan', methods=['POST'])
@login_required
def process_scan():
    data = request.get_json()
    files_to_process = data.get('files', [])
    
    if not files_to_process:
        return jsonify({'success': False, 'message': 'ไม่ได้เลือกไฟล์'}), 400
        
    rules = db.get_rules(current_user.id)
    processed_count = 0
    errors_count = 0
    
    for file_path in files_to_process:
        if not os.path.exists(file_path):
            continue
            
        moved, msg, cat = process_file_move(file_path, rules, current_user.id)
        if moved:
            processed_count += 1
        elif "Error" in msg:
            errors_count += 1
            
    stats = get_category_stats(current_user.id)
    return jsonify({
        'success': True, 
        'message': f'จัดระเบียบสำเร็จ {processed_count} ไฟล์', 
        'stats': stats
    })

# --- Drive Scanner APIs (Method 3 Enhanced) ---

# System folders to skip during drive scan
SKIP_FOLDERS = {
    'Windows', 'Program Files', 'Program Files (x86)', 'ProgramData',
    '$Recycle.Bin', 'System Volume Information', 'Recovery', 'PerfLogs',
    'AppData', 'MSOCache', 'Config.Msi', '$WINDOWS.~BT', '$WINDOWS.~WS',
    'Documents and Settings', 'hiberfil.sys', 'pagefile.sys', 'swapfile.sys',
    'node_modules', '.git', '__pycache__', '.venv', 'venv', '.idea', '.vscode'
}

@app.route('/api/get_drives', methods=['GET'])
@login_required
def get_drives():
    """Get available drives on Windows"""
    drives = []
    if os.name == 'nt':  # Windows
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            drive = f'{letter}:\\'
            if os.path.exists(drive):
                try:
                    # Get drive info
                    total, used, free = shutil.disk_usage(drive)
                    drives.append({
                        'letter': letter,
                        'path': drive,
                        'total_gb': round(total / (1024**3), 1),
                        'free_gb': round(free / (1024**3), 1)
                    })
                except:
                    drives.append({'letter': letter, 'path': drive})
    else:
        # Linux/Mac - show root and common mount points
        drives.append({'letter': '/', 'path': '/'})
        
    return jsonify({'success': True, 'drives': drives})

@app.route('/api/scan_drive', methods=['GET'])
@login_required
def scan_drive():
    """
    Scan a drive with extension filtering and pagination.
    Optimized to stop scanning once limit is reached for faster performance.
    """
    drive = request.args.get('drive', '')
    extensions = request.args.get('extensions', '').lower().strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 100))
    
    if not drive:
        return jsonify({'success': False, 'message': 'กรุณาเลือก Drive'}), 400
    
    # Parse extensions (comma-separated)
    ext_filter = []
    if extensions:
        ext_filter = [e.strip().lstrip('.').lower() for e in extensions.split(',') if e.strip()]
    
    rules = db.get_rules(current_user.id)
    files_found = []
    files_matched = 0  # Count files that match filter
    
    def get_destination(file_ext):
        """Get destination folder based on rules"""
        for rule in rules:
            allowed_exts = [e.strip().lower() for e in rule['allowed_extensions'].split(',')]
            if file_ext in allowed_exts:
                return {
                    'category': rule['category_name'],
                    'folder': os.path.join(rule['target_folder_path'], rule['category_name'])
                }
        return None
    
    try:
        scan_complete = False
        
        for root, dirs, files in os.walk(drive):
            if scan_complete:
                break
                
            # Skip system folders
            dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS and not d.startswith('.')]
            
            for filename in files:
                # Skip hidden files
                if filename.startswith('.'):
                    continue
                    
                file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
                
                # Apply extension filter
                if ext_filter and file_ext not in ext_filter:
                    continue
                
                files_matched += 1
                
                # Skip files before offset for pagination
                if files_matched <= offset:
                    continue
                
                # Collect files up to limit + 1 (extra one to check has_more)
                if len(files_found) < limit + 1:
                    file_path = os.path.join(root, filename)
                    
                    try:
                        file_stat = os.stat(file_path)
                        file_size = file_stat.st_size
                        modified_time = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    except:
                        file_size = 0
                        modified_time = '-'
                    
                    dest_info = get_destination(file_ext)
                    
                    files_found.append({
                        'name': filename,
                        'path': file_path,
                        'source_folder': root,
                        'size': file_size,
                        'extension': file_ext,
                        'modified': modified_time,
                        'category': dest_info['category'] if dest_info else None,
                        'destination_folder': dest_info['folder'] if dest_info else None
                    })
                else:
                    # We have enough files, stop scanning
                    scan_complete = True
                    break
        
        # Check if there are more files
        has_more = len(files_found) > limit
        
        # Return only 'limit' files, not the extra one
        files_to_return = files_found[:limit]
        
        return jsonify({
            'success': True,
            'files': files_to_return,
            'count': len(files_to_return),
            'offset': offset,
            'limit': limit,
            'has_more': has_more,
            'next_offset': offset + limit if has_more else None,
            'drive': drive,
            'extensions': extensions or 'ทั้งหมด'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/process_drive_scan', methods=['POST'])
@login_required
def process_drive_scan():
    """Process selected files from drive scan"""
    data = request.get_json()
    files_to_process = data.get('files', [])
    
    if not files_to_process:
        return jsonify({'success': False, 'message': 'ไม่ได้เลือกไฟล์'}), 400
        
    rules = db.get_rules(current_user.id)
    processed_count = 0
    errors_count = 0
    errors_list = []
    
    for file_info in files_to_process:
        file_path = file_info if isinstance(file_info, str) else file_info.get('path', '')
        
        if not file_path or not os.path.exists(file_path):
            errors_count += 1
            continue
            
        moved, msg, cat = process_file_move(file_path, rules, current_user.id)
        if moved:
            processed_count += 1
        elif "Error" in msg:
            errors_count += 1
            errors_list.append(f"{os.path.basename(file_path)}: {msg}")
            
    stats = get_category_stats(current_user.id)
    return jsonify({
        'success': True, 
        'message': f'จัดระเบียบสำเร็จ {processed_count} ไฟล์, ผิดพลาด {errors_count} ไฟล์', 
        'processed_count': processed_count,
        'errors_count': errors_count,
        'stats': stats
    })



@app.route('/settings')
@login_required
def settings():
    rules = db.get_rules(current_user.id)
    return render_template('settings.html', rules=rules)

@app.route('/settings/add', methods=['POST'])
@login_required
def add_rule():
    category_name = request.form.get('category_name')
    target_folder = request.form.get('target_folder_path')
    extensions = request.form.get('allowed_extensions')

    if not category_name or not target_folder or not extensions:
        flash('กรุณากรอกข้อมูลให้ครบทุกช่อง', 'danger')
        return redirect(url_for('settings'))

    if db.add_rule(current_user.id, category_name, target_folder, extensions):
        flash('เพิ่มกฎเรียบร้อยแล้ว', 'success')
    else:
        flash('เกิดข้อผิดพลาดในการบันทึกข้อมูล', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/settings/delete/<rule_id>', methods=['POST'])
@login_required
def delete_rule(rule_id):
    if db.delete_rule(rule_id, current_user.id):
        flash('ลบกฎเรียบร้อยแล้ว', 'success')
    else:
         flash('เกิดข้อผิดพลาดในการลบข้อมูล', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/settings/add_defaults', methods=['POST'])
@login_required
def add_default_rules():
    default_rules = [
        ('รูปภาพ', 'Images', 'jpg, jpeg, png, gif, bmp, webp'),
        ('เอกสาร', 'Documents', 'pdf, doc, docx, txt, xls, xlsx, ppt, pptx'),
        ('วิดีโอ', 'Videos', 'mp4, mov, avi, mkv, wmv'),
        ('เพลง', 'Music', 'mp3, wav, flac, m4a'),
        ('บีบอัด', 'Archives', 'zip, rar, 7z, tar, gz')
    ]
    
    # Get user's home directory for default paths
    user_home = os.path.expanduser('~')
    
    success_count = 0
    for name, folder, exts in default_rules:
        # Construct target path (e.g., C:\Users\User\Images)
        target_path = os.path.join(user_home, folder)
        if db.add_rule(current_user.id, name, target_path, exts):
            success_count += 1
            
    if success_count > 0:
        flash(f'เพิ่มกฎแนะนำเรียบร้อยแล้ว {success_count} รายการ', 'success')
    else:
        flash('เกิดข้อผิดพลาดในการเพิ่มกฎ', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.get_by_username(username)
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('เข้าสู่ระบบสำเร็จ', 'success')
            return redirect(url_for('index'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user exists
        existing_user = User.get_by_username(username)
        if existing_user:
            flash('ชื่อผู้ใช้นี้ถูกใช้งานแล้ว', 'danger')
            return redirect(url_for('register'))
            
        password_hash = generate_password_hash(password)
        
        password_hash = generate_password_hash(password)
        
        if db.create_user(username, email, password_hash):
             flash('สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ', 'success')
             return redirect(url_for('login'))
        else:
             flash('เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล', 'danger')
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ออกจากระบบแล้ว', 'info')
    return redirect(url_for('login'))

# --- Bulk Operations ---

@app.route('/open_multiple_files', methods=['POST'])
@login_required
def open_multiple_files():
    data = request.get_json()
    log_ids = data.get('log_ids', [])
    
    if not log_ids:
        return jsonify({'success': False, 'message': 'ไม่ได้เลือกไฟล์'}), 400
        
    success_count = 0
    errors = []
    
    for log_id in log_ids:
        file_record = db.get_file_by_id(log_id, current_user.id)
        if file_record and os.path.exists(file_record['destination_path']):
            try:
                os.startfile(file_record['destination_path'])
                success_count += 1
            except Exception as e:
                errors.append(f"Error opening {file_record['filename']}: {str(e)}")
        else:
             errors.append(f"File not found: {log_id}")
             
    if success_count > 0:
        return jsonify({'success': True, 'message': f'เปิดไฟล์สำเร็จ {success_count} ไฟล์'})
    else:
        return jsonify({'success': False, 'message': 'ไม่สามารถเปิดไฟล์ได้', 'errors': errors})

@app.route('/download_multiple_files', methods=['POST'])
@login_required
def download_multiple_files():
    data = request.get_json()
    log_ids = data.get('log_ids', [])
    
    if not log_ids:
         return jsonify({'success': False, 'message': 'ไม่ได้เลือกไฟล์'}), 400
         
    # Create ZIP
    try:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for log_id in log_ids:
                file_record = db.get_file_by_id(log_id, current_user.id)
                if file_record and os.path.exists(file_record['destination_path']):
                    # Add file to zip
                    zf.write(file_record['destination_path'], arcname=file_record['filename'])
        
        memory_file.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'files_archive_{timestamp}.zip'
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete_multiple_files', methods=['POST'])
@login_required
def delete_multiple_files():
    data = request.get_json()
    log_ids = data.get('log_ids', [])
    
    if not log_ids:
         return jsonify({'success': False, 'message': 'ไม่ได้เลือกไฟล์'}), 400
         
    deleted_count = 0
    
    for log_id in log_ids:
        try:
             file_record = db.get_file_by_id(log_id, current_user.id)
             if file_record:
                 # Delete from disk
                 if os.path.exists(file_record['destination_path']):
                     try: os.remove(file_record['destination_path'])
                     except: pass
                 # Delete from DB
                 db.delete_file_log(log_id)
                 deleted_count += 1
        except:
            continue
            
    return jsonify({'success': True, 'message': f'ลบไฟล์สำเร็จ {deleted_count} ไฟล์'})

@app.route('/rename_multiple_files', methods=['POST'])
@login_required
def rename_multiple_files():
    data = request.get_json()
    log_ids = data.get('log_ids', [])
    base_name = data.get('base_name')
    
    if not log_ids or not base_name:
         return jsonify({'success': False, 'message': 'ข้อมูลไม่ครบถ้วน'}), 400
    
    processed_count = 0
    errors = []
    
    # Sort IDs to ensure consistent numbering (optional, but good)
    # We assume simple iteration order
    
    for index, log_id in enumerate(log_ids):
        try:
            file_record = db.get_file_by_id(log_id, current_user.id)
            if not file_record: continue
            
            old_path = file_record['destination_path']
            directory = os.path.dirname(old_path)
            ext = file_record['extension']
            if not ext.startswith('.'): ext = '.' + ext
            
            # Pattern: BaseName (1).ext
            new_filename = f"{base_name} ({index + 1}){ext}"
            new_path = os.path.join(directory, new_filename)
            
            if os.path.exists(new_path):
                 # Skip if collision
                 errors.append(f"Skipped {file_record['filename']}: Target exists.")
                 continue
            
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                db.update_file_path(log_id, new_filename, new_path)
                processed_count += 1
        except Exception as e:
            errors.append(str(e))
            
    return jsonify({'success': True, 'message': f'เปลี่ยนชื่อสำเร็จ {processed_count} ไฟล์', 'processed_count': processed_count})


@app.route('/api/select_folder_dialog')
@login_required
def select_folder_dialog():
    """
    Opens a native folder selection dialog on the server (host machine).
    Uses Tkinter to spawn the dialog.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Create a hidden root window
        root = tk.Tk()
        root.withdraw() # Hide the main window
        
        # Make sure it appears on top
        root.attributes('-topmost', True)
        
        # Open the dialog
        folder_path = filedialog.askdirectory(title="เลือกโฟลเดอร์สำหรับจัดระเบียบ")
        
        # Clean up
        root.destroy()
        
        if folder_path:
            # Normalize path for Windows
            folder_path = os.path.normpath(folder_path)
            return jsonify({'success': True, 'path': folder_path})
        else:
            return jsonify({'success': False, 'message': 'User cancelled'})
            
    except Exception as e:
        print(f"Error opening dialog: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    # Ensure database is initialized
    # db.init_db() # Note: The original code didn't have explicit init_db in main block, respecting original structure
    app.run(debug=True)
