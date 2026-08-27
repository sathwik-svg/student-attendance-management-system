from flask import Blueprint, jsonify, request
import os
import pymysql
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

dashboard_api = Blueprint("dashboard_api", __name__, url_prefix="/api/dashboard")


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "attendance_app"),
        password=os.getenv("DB_PASSWORD", "AttendX_DB_2006!"),
        database=os.getenv("DB_NAME", "student_attendance"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


@dashboard_api.route("/stats")
def stats():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM students")
            students = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM faculty")
            faculty = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM classes")
            classes = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM subjects")
            subjects = cursor.fetchone()["total"]

            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    COALESCE(
                        ROUND(
                            SUM(status = 'PRESENT') / NULLIF(COUNT(*), 0) * 100,
                            1
                        ),
                        0
                    ) AS percentage
                FROM attendance
                WHERE attendance_date = CURDATE()
            """)
            attendance = cursor.fetchone()

        return jsonify({
            "success": True,
            "students": students,
            "faculty": faculty,
            "classes": classes,
            "subjects": subjects,
            "attendance_today": float(attendance["percentage"] or 0),
            "attendance_records_today": attendance["total"]
        })

    finally:
        connection.close()


@dashboard_api.route("/weekly")
def weekly():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    DAYNAME(attendance_date) AS day_name,
                    ROUND(
                        SUM(status = 'PRESENT') /
                        NULLIF(COUNT(*), 0) * 100,
                        1
                    ) AS percentage
                FROM attendance
                WHERE attendance_date >= CURDATE() - INTERVAL 6 DAY
                GROUP BY attendance_date, DAYNAME(attendance_date)
                ORDER BY attendance_date
            """)

            rows = cursor.fetchall()

        return jsonify({
            "success": True,
            "data": rows
        })

    finally:
        connection.close()


@dashboard_api.route("/activity")
def activity():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    al.action,
                    al.old_status,
                    al.new_status,
                    al.created_at,
                    u.username
                FROM attendance_logs al
                LEFT JOIN users u ON u.id = al.user_id
                ORDER BY al.created_at DESC
                LIMIT 8
            """)

            rows = cursor.fetchall()

            for row in rows:
                if row["created_at"]:
                    row["created_at"] = row["created_at"].isoformat()

        return jsonify({
            "success": True,
            "data": rows
        })

    finally:
        connection.close()


@dashboard_api.route("/system")
def system():
    database = "OFFLINE"

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version")
            mysql_version = cursor.fetchone()["version"]

        connection.close()
        database = "ONLINE"

    except Exception:
        mysql_version = "Unavailable"

    return jsonify({
        "success": True,
        "server": "home-server",
        "database": database,
        "mysql_version": mysql_version,
        "api": "ONLINE",
        "application": "ONLINE"
    })


# ============================================================
# ATTENDX ADMIN MANAGEMENT API
# ============================================================

from werkzeug.security import generate_password_hash


def admin_connection():
    return get_connection()


@dashboard_api.get("/management")
def management_summary():
    connection = admin_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, code FROM departments ORDER BY name")
            departments = cursor.fetchall()

            cursor.execute("""
                SELECT c.id, c.name, c.year, c.semester, c.section,
                       d.name AS department_name, d.code AS department_code
                FROM classes c
                JOIN departments d ON d.id = c.department_id
                ORDER BY c.year, c.semester, c.name, c.section
            """)
            classes = cursor.fetchall()

            cursor.execute("""
                SELECT s.id, s.name, s.code,
                       d.name AS department_name, d.code AS department_code
                FROM subjects s
                JOIN departments d ON d.id = s.department_id
                ORDER BY s.name
            """)
            subjects = cursor.fetchall()

            cursor.execute("""
                SELECT f.id, f.employee_id,
                       u.id AS user_id, u.username, u.full_name, u.email,
                       d.name AS department_name, d.code AS department_code
                FROM faculty f
                JOIN users u ON u.id = f.user_id
                JOIN departments d ON d.id = f.department_id
                WHERE u.role = 'FACULTY'
                ORDER BY u.full_name
            """)
            faculty = cursor.fetchall()

            cursor.execute("""
                SELECT id, username, full_name, email, is_active
                FROM users
                WHERE role = 'HOD'
                ORDER BY full_name
            """)
            hods = cursor.fetchall()

            cursor.execute("""
                SELECT s.id, s.roll_number, s.admission_year,
                       u.id AS user_id, u.username, u.full_name, u.email,
                       c.name AS class_name, c.year, c.semester, c.section,
                       d.name AS department_name, d.code AS department_code
                FROM students s
                JOIN users u ON u.id = s.user_id
                JOIN classes c ON c.id = s.class_id
                JOIN departments d ON d.id = c.department_id
                ORDER BY s.roll_number
            """)
            students = cursor.fetchall()

        return jsonify({
            "success": True,
            "departments": departments,
            "classes": classes,
            "subjects": subjects,
            "faculty": faculty,
            "hods": hods,
            "students": students
        })

    finally:
        connection.close()


@dashboard_api.post("/departments")
def create_department():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    code = str(data.get("code", "")).strip().upper()

    if not name or not code:
        return jsonify({
            "success": False,
            "error": "Department name and code are required"
        }), 400

    connection = admin_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO departments (name, code) VALUES (%s, %s)",
                (name, code)
            )

        return jsonify({
            "success": True,
            "message": "Department created"
        }), 201

    except pymysql.err.IntegrityError:
        return jsonify({
            "success": False,
            "error": "Department name or code already exists"
        }), 409

    finally:
        connection.close()


@dashboard_api.post("/classes")
def create_class():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    department_id = data.get("department_id")
    year = data.get("year")
    semester = data.get("semester")
    section = str(data.get("section", "")).strip().upper()

    if not all([name, department_id, year, semester, section]):
        return jsonify({
            "success": False,
            "error": "All class fields are required"
        }), 400

    connection = admin_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO classes
                (name, department_id, year, semester, section)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, department_id, year, semester, section))

        return jsonify({
            "success": True,
            "message": "Class created"
        }), 201

    except pymysql.err.IntegrityError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 409

    finally:
        connection.close()


@dashboard_api.post("/subjects")
def create_subject():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    code = str(data.get("code", "")).strip().upper()
    department_id = data.get("department_id")

    if not name or not code or not department_id:
        return jsonify({
            "success": False,
            "error": "Subject name, code and department are required"
        }), 400

    connection = admin_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO subjects (name, code, department_id)
                VALUES (%s, %s, %s)
            """, (name, code, department_id))

        return jsonify({
            "success": True,
            "message": "Subject created"
        }), 201

    except pymysql.err.IntegrityError:
        return jsonify({
            "success": False,
            "error": "Subject code already exists"
        }), 409

    finally:
        connection.close()


@dashboard_api.post("/faculty")
def create_faculty():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip() or None
    employee_id = str(data.get("employee_id", "")).strip().upper()
    department_id = data.get("department_id")

    if not all([username, password, full_name, employee_id, department_id]):
        return jsonify({
            "success": False,
            "error": "Username, password, name, employee ID and department are required"
        }), 400

    connection = admin_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users
                (username, password_hash, role, full_name, email)
                VALUES (%s, %s, 'FACULTY', %s, %s)
            """, (
                username,
                generate_password_hash(password),
                full_name,
                email
            ))

            user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO faculty
                (user_id, employee_id, department_id)
                VALUES (%s, %s, %s)
            """, (user_id, employee_id, department_id))

        return jsonify({
            "success": True,
            "message": "Faculty created",
            "user_id": user_id
        }), 201

    except pymysql.err.IntegrityError as e:
        connection.rollback()
        return jsonify({
            "success": False,
            "error": "Username, email or employee ID already exists"
        }), 409

    finally:
        connection.close()


@dashboard_api.post("/hods")
def create_hod():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip() or None

    if not all([username, password, full_name]):
        return jsonify({
            "success": False,
            "error": "Username, password and full name are required"
        }), 400

    connection = admin_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users
                (username, password_hash, role, full_name, email)
                VALUES (%s, %s, 'HOD', %s, %s)
            """, (
                username,
                generate_password_hash(password),
                full_name,
                email
            ))

        return jsonify({
            "success": True,
            "message": "HOD created"
        }), 201

    except pymysql.err.IntegrityError:
        return jsonify({
            "success": False,
            "error": "Username or email already exists"
        }), 409

    finally:
        connection.close()


@dashboard_api.post("/students")
def create_student():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip() or None
    roll_number = str(data.get("roll_number", "")).strip().upper()
    class_id = data.get("class_id")
    admission_year = data.get("admission_year")

    if not all([username, password, full_name, roll_number, class_id]):
        return jsonify({
            "success": False,
            "error": "Username, password, name, roll number and class are required"
        }), 400

    connection = admin_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users
                (username, password_hash, role, full_name, email)
                VALUES (%s, %s, 'STUDENT', %s, %s)
            """, (
                username,
                generate_password_hash(password),
                full_name,
                email
            ))

            user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO students
                (user_id, roll_number, class_id, admission_year)
                VALUES (%s, %s, %s, %s)
            """, (
                user_id,
                roll_number,
                class_id,
                admission_year
            ))

        return jsonify({
            "success": True,
            "message": "Student created",
            "user_id": user_id
        }), 201

    except pymysql.err.IntegrityError:
        connection.rollback()
        return jsonify({
            "success": False,
            "error": "Username, email or roll number already exists"
        }), 409

    finally:
        connection.close()
