# 🎓 Bilimdonlar — Test Platformasi

Python (Flask) + MySQL + Telegram bot asosida qurilgan bilimdonlik test platformasi.
Foydalanuvchilar veb-sayt orqali testlarni vaqt chegarasida topshiradi, ball va
sarflangan vaqt bo'yicha g'oliblar aniqlanadi. Administrator testlarni, savollarni
va foydalanuvchilarni boshqaradi. Telegram bot orqali har bir ishtirokchiga shaxsiy
natijasi va g'oliblar e'loni avtomatik yuboriladi.

## Imkoniyatlar

- **Login/parol tizimi** — ro'yxatdan o'tish, kirish, parollar xavfsiz hashlanadi (Werkzeug)
- **Foydalanuvchi paneli** — faol testlar ro'yxati, testni boshlash/davom ettirish, natijalar
- **Vaqt chegarasi** — har bir test uchun umumiy vaqt; vaqt tugasa, test avtomatik topshiriladi
  (frontendda JS taymer + backendda xavfsizlik tekshiruvi — soatni "aldab" bo'lmaydi)
- **G'oliblarni aniqlash** — ball bo'yicha, teng bo'lsa kamroq vaqt sarflagan g'olib
- **Admin paneli** — test va savol qo'shish/tahrirlash/o'chirish, testni faollashtirish,
  natijalarni ko'rish, foydalanuvchilarni boshqarish (admin qilish, bloklash, o'chirish)
- **Telegram bot** — hisobni ulash (`/start <kod>`), shaxsiy natijalarni ko'rish (`/natija`),
  faol testlar ro'yxati (`/reyting`); admin "G'oliblarni e'lon qilish" tugmasini bossa,
  top-3 g'olibga avtomatik xabar boradi

## Texnologiyalar

| Qatlam | Texnologiya |
|---|---|
| Backend | Python 3, Flask |
| Ma'lumotlar bazasi | MySQL / MariaDB (PyMySQL) |
| Frontend | Jinja2 shablonlar, vanilla CSS, vanilla JS |
| Bot | Telegram Bot API (long polling, qo'shimcha kutubxonasiz) |

## Loyihaning tuzilishi

```
bilimdonlar/
├── app.py                # Flask ilovasi (entry point)
├── config.py              # .env dan sozlamalarni o'qiydi
├── db.py                  # MySQL ulanish yordamchisi
├── auth_utils.py           # login_required / admin_required dekoratorlari
├── telegram_utils.py       # Telegram xabar YUBORISH (Flask ichidan)
├── telegram_bot.py         # Alohida ishlaydigan bot (xabar QABUL qilish)
├── create_admin.py         # Birinchi admin hisobini yaratish skripti
├── schema.sql              # MySQL jadvallari
├── requirements.txt
├── .env.example             # Sozlamalar namunasi
├── routes/
│   ├── auth.py             # ro'yxatdan o'tish / kirish / chiqish
│   ├── user.py              # foydalanuvchi: testlar, natijalar, reyting, profil
│   └── admin.py             # admin: testlar, savollar, natijalar, foydalanuvchilar
├── templates/               # Jinja2 HTML shablonlar
│   └── admin/
└── static/
    ├── css/style.css
    └── js/ (main.js, test_timer.js)
```

## O'rnatish

### 1. Talablar

- Python 3.10+
- MySQL yoki MariaDB server
- Telegram bot tokeni ([@BotFather](https://t.me/BotFather) orqali bepul olinadi)

### 2. Repozitoriyani tayyorlash

```bash
cd bilimdonlar
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Ma'lumotlar bazasini yaratish

```bash
mysql -u root -p < schema.sql
```

Bu `bilimdonlar` nomli baza va barcha jadvallarni yaratadi.

### 4. Sozlamalar (.env)

```bash
cp .env.example .env
```

`.env` faylini oching va quyidagilarni to'ldiring:

```
SECRET_KEY=tasodifiy-uzun-maxfiy-satr
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=parolingiz
MYSQL_DB=bilimdonlar
TELEGRAM_BOT_TOKEN=BotFather-dan-olingan-token
TELEGRAM_BOT_USERNAME=SizningBotUsername
```

> `TELEGRAM_BOT_TOKEN` bo'sh qoldirilsa, sayt to'liq ishlayveradi — faqat Telegram
> xabarlari yuborilmaydi (xato bermaydi, jim o'tkazib yuboradi).

### 5. Birinchi admin hisobini yaratish

```bash
python create_admin.py
```

Ism, login va parolni kiriting — shu hisob bilan `/admin` panelga kirasiz.

### 6. Ilovani ishga tushirish

```bash
python app.py
```

Brauzerda oching: **http://localhost:5000**

### 7. Telegram botni ishga tushirish (ixtiyoriy, alohida terminalda)

```bash
python telegram_bot.py
```

Bu jarayon doimiy ishlab turishi kerak (masalan, serverda `systemd`, `screen`,
`tmux` yoki `pm2`/`supervisor` orqali). Botni 24/7 ishlatish uchun uni serverga
joylab, qayta ishga tushirilishini ta'minlang.

## Foydalanish oqimi

1. **Admin**: tizimga kirib, "+ Yangi test" orqali test yaratadi, savollar qo'shadi
   (4 variant, to'g'ri javob, ball), so'ng testni **faollashtiradi**.
2. **Foydalanuvchi**: ro'yxatdan o'tadi, faol testni tanlab "Boshlash" tugmasini bosadi.
   Sahifa tepasida taymer ko'rinadi — vaqt tugaguncha javob berib ulguradi.
   Vaqt tugasa, mavjud javoblar bilan test avtomatik topshiriladi.
3. **Natija**: foydalanuvchi o'z ballini, sarflagan vaqtini va reytingdagi o'rnini
   darhol ko'radi, javoblari tahlilini (qaysi to'g'ri/noto'g'ri) ko'rib chiqadi.
4. **Telegram**: profil sahifasida "Telegramni ulash" tugmasi bosiladi → bot ochiladi →
   `/start <kod>` avtomatik yuboriladi → hisob ulanadi. Shundan keyin har bir test
   natijasi va g'oliblar e'loni shu Telegramga ham keladi.
5. **G'oliblarni e'lon qilish**: admin testning natijalar sahifasida
   "🏆 G'oliblarni e'lon qilish" tugmasini bosadi — top-3 ishtirokchiga (agar
   Telegram ulangan bo'lsa) avtomatik xabar yuboriladi.

## Xavfsizlik bo'yicha eslatma (production uchun)

Bu loyiha to'liq ishlaydigan, lekin **o'quv/boshlang'ich darajadagi** platforma sifatida
qurilgan. Real foydalanuvchilar bilan ishga tushirishdan oldin quyidagilarni qo'shish tavsiya etiladi:

- HTTPS (masalan, Nginx + Let's Encrypt orqali)
- CSRF himoyasi (Flask-WTF)
- So'rovlar sonini cheklash (rate limiting), ayniqsa `/auth/login` uchun
- Production WSGI server (gunicorn/uwsgi) — `python app.py` faqat ishlab chiqish uchun
- Muntazam zaxira nusxa (backup) MySQL bazasidan

## Litsenziya

Ushbu kod sizning loyihangiz uchun erkin tarzda ishlatilishi, o'zgartirilishi va
joylashtirilishi mumkin.
