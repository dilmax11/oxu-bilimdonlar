-- Real vaqtli monitoring uchun: bir natija (result) ichida bir savolga
-- faqat bitta javob qatori bo'lishi kerak, shunda "javobni yangilash"
-- (ON DUPLICATE KEY UPDATE) ishlaydi.
--
-- Ishga tushirish: mysql -u root -p bilimdonlar < migrate_add_answers_unique.sql
--
-- Eslatma: agar avval (eski versiyada) bitta result_id+question_id uchun
-- bir nechta qator hosil bo'lgan bo'lsa, quyidagi qator avval ortiqchalarini
-- tozalaydi (har biridan eng so'nggisini qoldiradi), keyin unique key qo'yadi.

DELETE a1 FROM answers a1
INNER JOIN answers a2
    ON a1.result_id = a2.result_id
   AND a1.question_id = a2.question_id
   AND a1.id < a2.id;

ALTER TABLE answers
    ADD UNIQUE KEY uniq_result_question (result_id, question_id);
