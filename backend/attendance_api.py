from flask import Blueprint, jsonify, request, session
import os
import pymysql

attendance_api = Blueprint(
    "attendance_api",
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

def logged_in():
    return bool(session.get("user_id"))

def faculty_admin():
    return session.get("role") in ("FACULTY", "ADMIN")

def deny(message="Authentication required"):
    return jsonify({"success": False, "error": message}), 403

# =========================================================
# ATTENDANCE — LIST
# =========================================================

@attendance_api.get("/attendance")
def list_attendance():
    if not logged_in():
        return deny()

    connection = db()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    a.id,
                    a.attendance_date,
                    a.status,
                    s.id AS student_id,
                    s.roll_number,
                    u.full_name AS student_name,
                    sub.id AS subject_id,
                    sub.name AS subject_name,
                    sub.code AS subject_code,
                    c.id AS class_id,
                    c.name AS class_name,
                    c.section
                FROM attendance a
                JOIN students s ON s.id = a.student_id
                JOIN users u ON u.id = s.user_id
                JOIN subjects sub ON sub.id = a.subject_id
                JOIN classes c ON c.id = a.class_id
                ORDER BY a.attendance_date DESC, s.roll_number
                LIMIT 500
            """)

            data = cursor.fetchall()

        return jsonify({
            "success": True,
            "data": data
        })

    finally:
        connection.close()

# =========================================================
# ATTENDANCE — MARK
# =========================================================

@attendance_api.post("/attendance")
def mark_attendance():
    if not logged_in():
        return deny()

    if not faculty_admin():
        return deny("Faculty or administrator access required")

    data = request.get_json(silent=True) or {}

    required = [
        "student_id",
        "subject_id",
        "class_id",
        "attendance_date",
        "status"
    ]

    if any(str(data.get(x, "")).strip() == "" for x in required):
        return jsonify({
            "success": False,
            "error": "All attendance fields are required"
        }), 400

    status = str(data["status"]).upper()

    if status not in ("PRESENT", "ABSENT"):
        return jsonify({
            "success": False,
            "error": "Status must be PRESENT or ABSENT"
        }), 400

    connection = db()

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT id
                FROM attendance
                WHERE student_id = %s
                  AND subject_id = %s
                  AND attendance_date = %s
            """, (
                int(data["student_id"]),
                int(data["subject_id"]),
                data["attendance_date"]
            ))

            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE attendance
                    SET status = %s,
                        class_id = %s,
                        marked_by = %s
                    WHERE id = %s
                """, (
                    status,
                    int(data["class_id"]),
                    session["user_id"],
                    existing["id"]
                ))

                attendance_id = existing["id"]
                action = "UPDATE"

            else:
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
                    int(data["student_id"]),
                    int(data["subject_id"]),
                    int(data["class_id"]),
                    data["attendance_date"],
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
                    new_status,
                    ip_address
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                attendance_id,
                session["user_id"],
                action,
                status,
                request.remote_addr
            ))

        return jsonify({
            "success": True,
            "id": attendance_id,
            "message": "Attendance saved"
        })

    finally:
        connection.close()

# =========================================================
# STUDENT ATTENDANCE CALCULATION
# =========================================================

@attendance_api.get("/attendance/student/<int:student_id>")
def student_attendance(student_id):
    if not logged_in():
        return deny()

    connection = db()

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    sub.id AS subject_id,
                    sub.name AS subject_name,
                    sub.code AS subject_code,
                    COUNT(a.id) AS classes_conducted,
                    COALESCE(
                        SUM(a.status = 'PRESENT'),
                        0
                    ) AS classes_attended,
                    COALESCE(
                        SUM(a.status = 'ABSENT'),
                        0
                    ) AS classes_absent,
                    COALESCE(
                        ROUND(
                            SUM(a.status = 'PRESENT') /
                            NULLIF(COUNT(a.id), 0) * 100,
                            2
                        ),
                        0
                    ) AS percentage
                FROM subjects sub
                LEFT JOIN attendance a
                    ON a.subject_id = sub.id
                   AND a.student_id = %s
                GROUP BY
                    sub.id,
                    sub.name,
                    sub.code
                ORDER BY sub.code
            """, (student_id,))

            subjects = cursor.fetchall()

            cursor.execute("""
                SELECT
                    COUNT(*) AS classes_conducted,
                    COALESCE(SUM(status = 'PRESENT'), 0)
                        AS classes_attended,
                    COALESCE(SUM(status = 'ABSENT'), 0)
                        AS classes_absent,
                    COALESCE(
                        ROUND(
                            SUM(status = 'PRESENT') /
                            NULLIF(COUNT(*), 0) * 100,
                            2
                        ),
                        0
                    ) AS percentage
                FROM attendance
                WHERE student_id = %s
            """, (student_id,))

            overall = cursor.fetchone()

        for row in subjects:
            row["status"] = (
                "ELIGIBLE"
                if float(row["percentage"] or 0) >= 75
                else "SHORTAGE"
            )

        overall["status"] = (
            "ELIGIBLE"
            if float(overall["percentage"] or 0) >= 75
            else "SHORTAGE"
        )

        return jsonify({
            "success": True,
            "student_id": student_id,
            "subjects": subjects,
            "overall": overall
        })

    finally:
        connection.close()

# =========================================================
# REPORT
# =========================================================

@attendance_api.get("/reports/attendance")
def attendance_report():
    if not logged_in():
        return deny()

    connection = db()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    s.roll_number,
                    u.full_name AS student_name,
                    c.name AS class_name,
                    c.section,
                    sub.code AS subject_code,
                    sub.name AS subject_name,
                    COUNT(a.id) AS classes_conducted,
                    COALESCE(SUM(a.status = 'PRESENT'), 0)
                        AS classes_attended,
                    COALESCE(SUM(a.status = 'ABSENT'), 0)
                        AS classes_absent,
                    COALESCE(
                        ROUND(
                            SUM(a.status = 'PRESENT') /
                            NULLIF(COUNT(a.id), 0) * 100,
                            2
                        ),
                        0
                    ) AS percentage
                FROM attendance a
                JOIN students s ON s.id = a.student_id
                JOIN users u ON u.id = s.user_id
                JOIN classes c ON c.id = a.class_id
                JOIN subjects sub ON sub.id = a.subject_id
                GROUP BY
                    s.id,
                    s.roll_number,
                    u.full_name,
                    c.name,
                    c.section,
                    sub.id,
                    sub.code,
                    sub.name
                ORDER BY
                    c.name,
                    c.section,
                    s.roll_number,
                    sub.code
            """)

            data = cursor.fetchall()

        for row in data:
            row["status"] = (
                "ELIGIBLE"
                if float(row["percentage"] or 0) >= 75
                else "SHORTAGE"
            )

        return jsonify({
            "success": True,
            "data": data
        })

    finally:
        connection.close()

# =========================================================
# ACTIVITY LOGS
# =========================================================

@attendance_api.get("/logs")
def logs():
    if not logged_in():
        return deny()

    connection = db()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    al.id,
                    al.action,
                    al.old_status,
                    al.new_status,
                    al.ip_address,
                    al.created_at,
                    u.username,
                    u.full_name
                FROM attendance_logs al
                LEFT JOIN users u
                    ON u.id = al.user_id
                ORDER BY al.created_at DESC
                LIMIT 100
            """)

            data = cursor.fetchall()

        for row in data:
            if row["created_at"]:
                row["created_at"] = row["created_at"].isoformat()

        return jsonify({
            "success": True,
            "data": data
        })

    finally:
        connection.close()
