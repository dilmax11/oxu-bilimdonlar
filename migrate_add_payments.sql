-- Pullik/bepul testlar va to'lov tasdiqlash funksiyasini qo'shish uchun migratsiya.
-- Ishga tushirish: mysql -u root -p bilimdonlar < migrate_add_payments.sql
-- DIQQAT: bu skriptni faqat BIR MARTA ishga tushiring (ustunlar allaqachon mavjud
-- bo'lsa, "Duplicate column" xatosi chiqishi mumkin — bu normal, e'tibor bermang).

ALTER TABLE tests
    ADD COLUMN is_paid TINYINT(1) NOT NULL DEFAULT 0 AFTER prize_info,
    ADD COLUMN price   INT NOT NULL DEFAULT 0 AFTER is_paid;

CREATE TABLE IF NOT EXISTS settings (
    name   VARCHAR(64) PRIMARY KEY,
    value  VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

INSERT INTO settings (name, value) VALUES
    ('payment_card_number', '0000 0000 0000 0000'),
    ('payment_card_owner', 'F.I.SH. kiritilmagan')
ON DUPLICATE KEY UPDATE name = name;

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
