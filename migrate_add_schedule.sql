-- Mavjud bilimdonlar bazasiga yangi ustunlar qo'shish (migration)
-- Faqat bir marta ishga tushiring:
--   mysql -u root -p < migrate_add_schedule.sql

USE bilimdonlar;

ALTER TABLE tests
    ADD COLUMN IF NOT EXISTS starts_at  DATETIME NULL DEFAULT NULL AFTER is_active,
    ADD COLUMN IF NOT EXISTS ends_at    DATETIME NULL DEFAULT NULL AFTER starts_at,
    ADD COLUMN IF NOT EXISTS prize_info VARCHAR(255) NULL DEFAULT NULL AFTER ends_at;
