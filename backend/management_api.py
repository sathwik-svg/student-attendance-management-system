from flask import Blueprint, jsonify, request, session
from functools import wraps
import os
import pymysql
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

management_api = Blueprint(
    "management_api",
    __name__,
    url_prefix="/api"
)


def db():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "attendance_app"),
        password=os.getenv("DB_PASSWORD", "AttendX_DB_2006!"),
        database=os.getenv("DB_NAME", "student_attendance"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def admin_required():
    return session.get("user_id") and session.get("role") == "ADMIN"


def faculty_or_admin():
    return session.get("user_id") and session.get("role") in ("FACULTY", "ADMIN")


def guard_admin():
    if not admin_required():
        return jsonify({
            "success": False,
            "error": "Administrator access required"
        }), 403
    return None


def guard_faculty():
    if not faculty_or_admin():
        return jsonify({
            "success": False,
            "error": "Faculty or administrator access required"
        }), 403
    return None


# =========================================================
# GENERIC HELPERS
# =========================================================

def rows(query, params=()):
    connection = db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    finally:
        connection.close()


def one(query, params=()):
    connection = db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    finally:
        connection.close()


# =========================================================
# DEPARTMENTS
# =========================================================

@management_api.get("/admin/departments")
def list_departments():
    error = guard_admin()
    if error:
        return error

    return jsonify({
        "success": True,
        "data": rows("""
            SELECT id, name, code, created_at
            FROM departments
            ORDER BY name
        """)
    })


@management_api.post("/admin/departments")
def create_department():
    error = guard_admin()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    code = str(data.get("code", "")).strip().upper()

    if not name or not code:
        return jsonify({
            "success": False,
            "error": "Name and code are required"
        }), 400

    connection = db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO departments (name, code) VALUES (%s, %s)",
                (name, code)
            )
            department_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "id": department_id,
            "message": "Department created"
        }), 201

    except pymysql.err.IntegrityError:
        return jsonify({
            "success": False,
            "error": "Department name or code already exists"
        }), 409
    finally:
        connection.close()


# =========================================================
# CLASSES
# =========================================================

@management_api.get("/admin/classes")
def list_classes():
    error = guard_admin()
    if error:
        return error

    return jsonify({
        "success": True,
        "data": rows("""
            SELECT
                c.id,
                c.name,
                c.year,
                c.semester,
                c.section,
                d.id AS department_id,
                d.name AS department_name,
                d.code AS department_code
            FROM classes c
            JOIN departments d ON d.id = c.department_id
            ORDER BY c.year, c.section, c.name
        """)
    })


@management_api.post("/admin/classes")
def create_class():
    error = guard_admin()
    if error:
        return error

    data = request.get_json(silent=True) or {}

    required = ["name", "department_id", "year", "semester", "section"]

    if any(str(data.get(x, "")).strip() == "" for x in required):
        return jsonify({
            "success": False,
            "error": "All class fields are required"
        }), 400

    connection = db()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO classes
                (name, department_id, year, semester, section)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                data["name"],
                int(data["department_id"]),
                int(data["year"]),
                int(data["semester"]),
                data["section"]
            ))

            class_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "id": class_id,
            "message": "Class created"
        }), 201

    finally:
        connection.close()


# =========================================================
# SUBJECTS
# =========================================================

@management_api.get("/admin/subjects")
def list_subjects():
    error = guard_admin()
    if error:
        return error

    return jsonify({
        "success": True,
        "data": rows("""
            SELECT
                s.id,
                s.name,
                s.code,
                d.id AS department_id,
                d.name AS department_name,
                d.code AS department_code
            FROM subjects s
            JOIN departments d ON d.id = s.department_id
            ORDER BY s.code
        """)
    })


@management_api.post("/admin/subjects")
def create_subject():
    error = guard_admin()
    if error:
        return error

    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    code = str(data.get("code", "")).strip().upper()
    department_id = data.get("department_id")

    if not name or not code or not department_id:
        return jsonify({
            "success": False,
            "error": "Name, code and department are required"
        }), 400

    connection = db()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO subjects
                (name, code, department_id)
                VALUES (%s, %s, %s)
            """, (name, code, int(department_id)))

            subject_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "id": subject_id,
            "message": "Subject created"
        }), 201

    except pymysql.err.IntegrityError:
        return jsonify({
            "success": False,
            "error": "Subject code already exists"
        }), 409
    finally:
        connection.close()


# =========================================================
# USERS / HOD
# =========================================================

@management_api.get("/admin/users")
def list_users():
    error = guard_admin()
    if error:
        return error

    return jsonify({
        "success": True,
        "data": rows("""
            SELECT
                id,
                username,
                role,
                full_name,
                email,
                is_active,
                created_at
            FROM users
            ORDER BY id DESC
        """)
    })


@management_api.post("/admin/users")
def create_user():
    error = guard_admin()
    if error:
        return error

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip() or None
    role = str(data.get("role", "")).strip().upper()

    if role not in ("STUDENT", "FACULTY", "HOD", "ADMIN"):
        return jsonify({
            "success": False,
            "error": "Invalid role"
        }), 400

    if not username or not password or not full_name:
        return jsonify({
            "success": False,
            "error": "Username, password and full name are required"
        }), 400

    connection = db()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users
                (username, password_hash, role, full_name, email)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                username,
                generate_password_hash(password),
                role,
                full_name,
                email
            ))

            user_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "id": user_id,
            "message": f"{role} user created"
        }), 201

    except pymysql.err.IntegrityError:
        return jsonify({
            "success": False,
            "error": "Username or email already exists"
        }), 409
    finally:
        connection.close()


# =========================================================
# FACULTY
# =========================================================

@management_api.get("/admin/faculty")
def list_faculty():
    error = guard_admin()
    if error:
        return error

    return jsonify({
        "success": True,
        "data": rows("""
            SELECT
                f.id,
                f.employee_id,
                u.username,
                u.full_name,
                u.email,
                u.role,
                d.name AS department_name,
                d.code AS department_code
            FROM faculty f
            JOIN users u ON u.id = f.user_id
            JOIN departments d ON d.id = f.department_id
            ORDER BY f.employee_id
        """)
    })


@management_api.post("/admin/faculty")
def create_faculty():
    error = guard_admin()
    if error:
        return error

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip() or None
    employee_id = str(data.get("employee_id", "")).strip()
    department_id = data.get("department_id")

    if not all([
        username,
        password,
        full_name,
        employee_id,
        department_id
    ]):
        return jsonify({
            "success": False,
            "error": "All faculty fields are required"
        }), 400

    connection = db()

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
            """, (
                user_id,
                employee_id,
                int(department_id)
            ))

        return jsonify({
            "success": True,
            "id": user_id,
            "message": "Faculty created"
        }), 201

    except pymysql.err.IntegrityError as e:
        connection.rollback()
        return jsonify({
            "success": False,
            "error": "Faculty username, email or employee ID already exists"
        }), 409
    finally:
        connection.close()


# =========================================================
# STUDENTS
# =========================================================

@management_api.get("/admin/students")
def list_students():
    error = guard_admin()
    if error:
        return error

    return jsonify({
        "success": True,
        "data": rows("""
            SELECT
                s.id,
                s.roll_number,
                s.admission_year,
                u.username,
                u.full_name,
                u.email,
                c.name AS class_name,
                c.year,
                c.semester,
                c.section,
                d.name AS department_name
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN classes c ON c.id = s.class_id
            JOIN departments d ON d.id = c.department_id
            ORDER BY s.roll_number
        """)
    })


@management_api.post("/admin/students")
def create_student():
    error = guard_admin()
    if error:
        return error

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip() or None
    roll_number = str(data.get("roll_number", "")).strip().upper()
    class_id = data.get("class_id")
    admission_year = data.get("admission_year")

    if not all([
        username,
        password,
        full_name,
        roll_number,
        class_id
    ]):
        return jsonify({
            "success": False,
            "error": "Username, password, name, roll number and class are required"
        }), 400

    connection = db()

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
                int(class_id),
                admission_year
            ))

        return jsonify({
            "success": True,
            "id": user_id,
            "message": "Student created"
        }), 201

    except pymysql.err.IntegrityError:
        connection.rollback()
        return jsonify({
            "success": False,
            "error": "Student username, email or roll number already exists"
        }), 409
    finally:
        connection.close()


# =========================================================
# ATTENDANCE
# =========================================================

@management_api.get("/attendance/students")
def attendance_students():
    error = guard_faculty()
    if error:
        return error

    class_id = request.args.get("class_id")

    if not class_id:
        return jsonify({
            "success": False,
            "error": "class_id is required"
        }), 400

    return jsonify({
        "success": True,
        "data": rows("""
            SELECT
                s.id,
                s.roll_number,
                u.full_name
            FROM students s
            JOIN users u ON u.id = s.user_id
            WHERE s.class_id = %s
            ORDER BY s.roll_number
        """, (class_id,))
    })


@management_api.post("/attendance/mark")
def mark_attendance():
    error = guard_faculty()
    if error:
        return error

    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    subject_id = data.get("subject_id")
    class_id = data.get("class_id")
    attendance_date = data.get("attendance_date")
    status = str(data.get("status", "")).upper()

    if not all([
        student_id,
        subject_id,
        class_id,
        attendance_date,
        status
    ]):
        return jsonify({
            "success": False,
            "error": "All attendance fields are required"
        }), 400

    if status not in ("PRESENT", "ABSENT"):
        return jsonify({
            "success": False,
            "error": "Status must be PRESENT or ABSENT"
        }), 400

    connection = db()

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT id, status
                FROM attendance
                WHERE student_id = %s
                AND subject_id = %s
                AND attendance_date = %s
            """, (
                student_id,
                subject_id,
                attendance_date
            ))

            existing = cursor.fetchone()

            if existing:
                old_status = existing["status"]

                cursor.execute("""
                    UPDATE attendance
                    SET status = %s,
                        class_id = %s,
                        marked_by = %s
                    WHERE id = %s
                """, (
                    status,
                    class_id,
                    session["user_id"],
                    existing["id"]
                ))

                action = "UPDATE"

                attendance_id = existing["id"]

            else:
                old_status = None

                cursor.execute("""
                    INSERT INTO attendance
                    (
                        student_id,
                        subject_id,
                        class_id,
                        attendance_date,
                        status,
                        marked_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    student_id,
                    subject_id,
                    class_id,
                    attendance_date,
                    status,
                    session["user_id"]
                ))

                attendance_id = cursor.lastrowid
                action = "CREATE"

            cursor.execute("""
                INSERT INTO attendance_logs
                (
                    attendance_id,
                    user_id,
                    action,
                    old_status,
                    new_status,
                    ip_address
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                attendance_id,
                session["user_id"],
                action,
                old_status,
                status,
                request.remote_addr
            ))

        return jsonify({
            "success": True,
            "attendance_id": attendance_id,
            "message": "Attendance saved"
        })

    finally:
        connection.close()


# =========================================================
# ATTENDANCE CALCULATION
# =========================================================

@management_api.get("/reports/student/<int:student_id>")
def student_report(student_id):
    if not session.get("user_id"):
        return jsonify({
            "success": False,
            "error": "Authentication required"
        }), 401

    data = rows("""
        SELECT
            s.id AS student_id,
            s.roll_number,
            u.full_name AS student_name,
            sub.id AS subject_id,
            sub.code,
            sub.name AS subject_name,
            COUNT(a.id) AS classes_conducted,
            SUM(a.status = 'PRESENT') AS classes_attended,
            SUM(a.status = 'ABSENT') AS classes_absent,
            ROUND(
                COALESCE(
                    SUM(a.status = 'PRESENT') /
                    NULLIF(COUNT(a.id), 0) * 100,
                    0
                ),
                1
            ) AS percentage
        FROM students s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN attendance a ON a.student_id = s.id
        LEFT JOIN subjects sub ON sub.id = a.subject_id
        WHERE s.id = %s
        GROUP BY
            s.id,
            s.roll_number,
            u.full_name,
            sub.id,
            sub.code,
            sub.name
        ORDER BY sub.code
    """, (student_id,))

    for item in data:
        percentage = float(item["percentage"] or 0)
        item["status"] = "ELIGIBLE" if percentage >= 75 else "SHORTAGE"

    return jsonify({
        "success": True,
        "data": data
    })


@management_api.get("/reports/overview")
def report_overview():
    if not session.get("user_id"):
        return jsonify({
            "success": False,
            "error": "Authentication required"
        }), 401

    result = one("""
        SELECT
            COUNT(*) AS total_records,
            COALESCE(SUM(status = 'PRESENT'), 0) AS present,
            COALESCE(SUM(status = 'ABSENT'), 0) AS absent,
            ROUND(
                COALESCE(
                    SUM(status = 'PRESENT') /
                    NULLIF(COUNT(*), 0) * 100,
                    0
                ),
                1
            ) AS percentage
        FROM attendance
    """)

    return jsonify({
        "success": True,
        "data": result
    })


# =========================================================
# HOD DEPARTMENT REPORT
# =========================================================

@management_api.get("/hod/overview")
def hod_overview():
    if session.get("role") not in ("HOD", "ADMIN"):
        return jsonify({
            "success": False,
            "error": "HOD or administrator access required"
        }), 403

    return jsonify({
        "success": True,
        "data": rows("""
            SELECT
                d.id,
                d.name,
                d.code,
                COUNT(DISTINCT s.id) AS students,
                COUNT(DISTINCT f.id) AS faculty,
                COUNT(DISTINCT sub.id) AS subjects,
                ROUND(
                    COALESCE(
                        SUM(a.status = 'PRESENT') /
                        NULLIF(COUNT(a.id), 0) * 100,
                        0
                    ),
                    1
                ) AS attendance_percentage
            FROM departments d
            LEFT JOIN classes c ON c.department_id = d.id
            LEFT JOIN students s ON s.class_id = c.id
            LEFT JOIN faculty f ON f.department_id = d.id
            LEFT JOIN subjects sub ON sub.department_id = d.id
            LEFT JOIN attendance a ON a.class_id = c.id
            GROUP BY d.id, d.name, d.code
            ORDER BY d.name
        """)
    })
