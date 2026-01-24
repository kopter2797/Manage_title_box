# Manage title box

โปรเจคจัดระเบียบไฟล์ Web Application ที่พัฒนาด้วย Python Flask และ MySQL (XAMPP)

## สิ่งที่ต้องมี (Prerequisites)

- Python 3.x
- XAMPP (สำหรับ MySQL Database) หรือ MongoDB Account
- Git

## การติดตั้งและการเริ่มใช้งาน (Installation & Setup)

1.  **Clone โปรเจค** (หรือดาวน์โหลดไฟล์)

    ```bash
    git clone <your-repo-url>
    cd project_thanawit
    ```

2.  **สร้างและเปิดใช้งาน Virtual Environment** (แนะนำ)

    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **ติดตั้ง Libraries ที่จำเป็น**

    ```bash
    pip install -r requirements.txt
    ```

4.  **ตั้งค่าฐานข้อมูล (Database)**

    - เปิด XAMPP และ Start Apache, MySQL
    - เข้า phpMyAdmin สร้างฐานข้อมูล `file_organizer_db`
    - Import `database/file_organizer_db.sql`

5.  **ตั้งค่า Config**
    - เปลี่ยนชื่อไฟล์ `config_example.py` เป็น `config.py`
    - แก้ไขค่าในไฟล์ตาม Database ที่ใช้

## การรันโปรแกรม (Running)

**แบบ Web Application (Flask)**

```bash
python app.py
```

เข้าใช้งานได้ที่ http://localhost:5000

**แบบ Desktop Application**

```bash
python desktop_main.py
```

## Structure

- `app.py`: ไฟล์หลัก Back-end
- `db_adapter.py`: ตัวจัดการฐานข้อมูล MySQL
- `desktop_main.py`: ไฟล์ Desktop App
- `templates/`: ไฟล์ HTML
- `static/`: ไฟล์ CSS/JS

## วิธีนำขึ้น GitHub & Render.com

1.  **อัพโค้ดขึ้น GitHub**

    ```bash
    git add .
    git commit -m "Update application"
    git push
    ```

2.  **Deploy บน Render.com**

    - สร้าง **Web Service** ใหม่ เลือก Repo เดิม
    - **Environment Variables**:
      - `DB_HOST`: Host ของ MySQL Server
      - `DB_USER`: Username ของ MySQL
      - `DB_PASSWORD`: Password ของ MySQL
      - `DB_NAME`: ชื่อฐานข้อมูล
      - `SECRET_KEY`: (รหัสลับอะไรก็ได้)
