-- Bilimdonlar test platformasi uchun ma'lumotlar bazasi sxemasi
-- Ishga tushirish: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS bilimdonlar
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE bilimdonlar;

-- Foydalanuvchilar (admin va oddiy foydalanuvchilar)
CREATE TABLE IF NOT EXISTS users (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    full_name           VARCHAR(150) NOT NULL,
    username            VARCHAR(50)  NOT NULL UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,
    role                ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    telegram_chat_id    VARCHAR(64)  DEFAULT NULL,
    telegram_link_code  VARCHAR(32)  DEFAULT NULL,
    is_blocked          TINYINT(1)   NOT NULL DEFAULT 0,
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Testlar (har bir test - bitta bilimdonlik tanlovi)
CREATE TABLE IF NOT EXISTS tests (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    title               VARCHAR(200) NOT NULL,
    description         TEXT,
    time_limit_minutes  INT NOT NULL DEFAULT 10,
    is_active           TINYINT(1) NOT NULL DEFAULT 0,
    starts_at           DATETIME NULL DEFAULT NULL,
    ends_at             DATETIME NULL DEFAULT NULL,
    prize_info          VARCHAR(255) NULL DEFAULT NULL,
    is_paid             TINYINT(1) NOT NULL DEFAULT 0,
    price               INT NOT NULL DEFAULT 0,
    created_by          INT NOT NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Savollar (har bir testga tegishli, 4 variantli)
CREATE TABLE IF NOT EXISTS questions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    test_id         INT NOT NULL,
    question_text   TEXT NOT NULL,
    option_a        VARCHAR(255) NOT NULL,
    option_b        VARCHAR(255) NOT NULL,
    option_c        VARCHAR(255) NOT NULL,
    option_d        VARCHAR(255) NOT NULL,
    correct_option  ENUM('A','B','C','D') NOT NULL,
    points          INT NOT NULL DEFAULT 1,
    order_no        INT NOT NULL DEFAULT 0,
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Natijalar (har bir foydalanuvchi har bir testni faqat bir marta topshiradi)
CREATE TABLE IF NOT EXISTS results (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT NOT NULL,
    test_id             INT NOT NULL,
    status              ENUM('in_progress','finished') NOT NULL DEFAULT 'in_progress',
    score               INT NOT NULL DEFAULT 0,
    total_points        INT NOT NULL DEFAULT 0,
    time_spent_seconds  INT DEFAULT NULL,
    started_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at         TIMESTAMP NULL DEFAULT NULL,
    UNIQUE KEY uniq_user_test (user_id, test_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Har bir savolga berilgan javoblar (tekshirish va statistika uchun)
CREATE TABLE IF NOT EXISTS answers (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    result_id       INT NOT NULL,
    question_id     INT NOT NULL,
    selected_option ENUM('A','B','C','D') DEFAULT NULL,
    is_correct      TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uniq_result_question (result_id, question_id),
    FOREIGN KEY (result_id) REFERENCES results(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Sayt sozlamalari (kalit-qiymat). To'lov uchun karta raqami va egasi shu yerda saqlanadi.
CREATE TABLE IF NOT EXISTS settings (
    name   VARCHAR(64) PRIMARY KEY,
    value  VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

INSERT INTO settings (name, value) VALUES
    ('payment_card_number', '0000 0000 0000 0000'),
    ('payment_card_owner', 'F.I.SH. kiritilmagan')
ON DUPLICATE KEY UPDATE name = name;

-- Pullik testlar uchun to'lov so'rovlari (foydalanuvchi chek yuklaydi, admin tasdiqlaydi)
CREATE TABLE IF NOT EXISTS payment_requests (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    test_id         INT NOT NULL,
    receipt_path    VARCHAR(255) NOT NULL,
    status          ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
    admin_comment   VARCHAR(255) DEFAULT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at     TIMESTAMP NULL DEFAULT NULL,
    reviewed_by     INT NULL DEFAULT NULL,
    UNIQUE KEY uniq_user_test_payment (user_id, test_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Boshlang'ich admin foydalanuvchi (parol: admin123 -- birinchi kirishdan keyin albatta o'zgartiring)
-- Parol hash python tomonidan generatsiya qilinadi, pastdagi qatorni create_admin.py orqali bajaring.
