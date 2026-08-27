CREATE DATABASE IF NOT EXISTS student_attendance;

USE student_attendance;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,

    username VARCHAR(100) NOT NULL UNIQUE,

    password_hash VARCHAR(255) NOT NULL,

    role ENUM(
        'STUDENT',
        'FACULTY',
        'HOD',
        'ADMIN'
    ) NOT NULL,

    full_name VARCHAR(150) NOT NULL,

    email VARCHAR(150) UNIQUE,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS departments (

    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(150) NOT NULL UNIQUE,

    code VARCHAR(20) NOT NULL UNIQUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS classes (

    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    department_id INT NOT NULL,

    year INT NOT NULL,

    semester INT NOT NULL,

    section VARCHAR(20) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS students (

    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL UNIQUE,

    roll_number VARCHAR(50) NOT NULL UNIQUE,

    class_id INT NOT NULL,

    admission_year INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (class_id)
        REFERENCES classes(id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS faculty (

    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL UNIQUE,

    employee_id VARCHAR(50) NOT NULL UNIQUE,

    department_id INT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (department_id)
        REFERENCES departments(id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS subjects (

    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(150) NOT NULL,

    code VARCHAR(50) NOT NULL UNIQUE,

    department_id INT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS attendance (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    student_id INT NOT NULL,

    subject_id INT NOT NULL,

    class_id INT NOT NULL,

    attendance_date DATE NOT NULL,

    status ENUM(
        'PRESENT',
        'ABSENT'
    ) NOT NULL,

    marked_by INT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY unique_attendance (
        student_id,
        subject_id,
        attendance_date
    ),

    FOREIGN KEY (student_id)
        REFERENCES students(id)
        ON DELETE CASCADE,

    FOREIGN KEY (subject_id)
        REFERENCES subjects(id)
        ON DELETE CASCADE,

    FOREIGN KEY (class_id)
        REFERENCES classes(id)
        ON DELETE CASCADE,

    FOREIGN KEY (marked_by)
        REFERENCES users(id)
);


CREATE TABLE IF NOT EXISTS attendance_logs (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    attendance_id BIGINT,

    user_id INT NOT NULL,

    action VARCHAR(50) NOT NULL,

    old_status VARCHAR(20),

    new_status VARCHAR(20),

    ip_address VARCHAR(45),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (attendance_id)
        REFERENCES attendance(id)
        ON DELETE SET NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);
