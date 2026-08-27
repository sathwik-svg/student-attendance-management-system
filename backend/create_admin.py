import pymysql
from werkzeug.security import generate_password_hash


DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "attendance_app",
    "password": "AttendX_DB_2026!",
    "database": "student_attendance",
}


USERNAME = "admin"
PASSWORD = "AttendX_Admin_2026!"
FULL_NAME = "System Administrator"
EMAIL = "admin@attendx.local"


connection = pymysql.connect(
    **DB_CONFIG,
    cursorclass=pymysql.cursors.DictCursor
)

try:
    password_hash = generate_password_hash(
        PASSWORD,
        method="scrypt"
    )

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s
            """,
            (USERNAME,)
        )

        existing = cursor.fetchone()

        if existing:

            cursor.execute(
                """
                UPDATE users
                SET
                    password_hash = %s,
                    role = 'ADMIN',
                    full_name = %s,
                    email = %s,
                    is_active = TRUE
                WHERE username = %s
                """,
                (
                    password_hash,
                    FULL_NAME,
                    EMAIL,
                    USERNAME
                )
            )

            print("✓ Existing admin updated")

        else:

            cursor.execute(
                """
                INSERT INTO users
                (
                    username,
                    password_hash,
                    role,
                    full_name,
                    email,
                    is_active
                )
                VALUES
                (%s, %s, 'ADMIN', %s, %s, TRUE)
                """,
                (
                    USERNAME,
                    password_hash,
                    FULL_NAME,
                    EMAIL
                )
            )

            print("✓ Admin account created")

    connection.commit()

finally:
    connection.close()


print()
print("================================")
print(" ATTENDX ADMIN READY")
print("================================")
print("Username:", USERNAME)
print("Role:     ADMIN")
print("================================")
