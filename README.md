# Qarz Bot

Aiogram 3.x + Firebase Realtime Database asosidagi qarzlarni boshqarish boti.

## Fayl strukturasi

```
qarzbot/
├── bot.py                  # Ishga tushirish (polling)
├── config.py                # .env / environment variables
├── database.py               # Firebase RTDB funksiyalari
├── states.py                  # FSM state guruhlari
├── handlers/
│   ├── start.py               # Ro'yxatdan o'tish + deep-link
│   ├── debts.py                # Haqdorlar/Qarzdorlar, qarz qo'shish
│   ├── finance.py               # Kirim/Chiqim (to'lovlar)
│   └── admin.py                  # /stats, /broadcast
├── keyboards/
│   ├── default.py                 # Reply klaviaturalar
│   └── inline.py                   # Inline klaviaturalar
├── services/
│   └── scheduler.py                 # APScheduler — 3 kunlik eslatmalar
├── locales/
│   └── texts.py                       # uz/ru/kk matnlar
├── requirements.txt
├── render.yaml
└── .env.example
```

## 1. Lokal ishga tushirish

```bash
cd qarzbot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env faylini to'ldiring: BOT_TOKEN, BOT_USERNAME, ADMIN_IDS, FIREBASE_DB_URL

# Firebase Console > Project settings > Service accounts > Generate new private key
# yuklab olingan JSON faylni loyiha ildiziga firebase_credentials.json nomi bilan qo'ying.

python bot.py
```

## 2. Firebase sozlash

1. https://console.firebase.google.com — yangi loyiha yarating.
2. **Build > Realtime Database** — bazani yarating (test rejimida boshlash mumkin, keyin
   Security Rules'ni faqat backend orqali yozish uchun cheklang).
3. **Project settings (⚙️) > Service accounts > Generate new private key** — JSON faylni yuklab oling.
4. Database URL'ni `.env` dagi `FIREBASE_DB_URL` ga yozing (masalan
   `https://your-project-default-rtdb.firebaseio.com`).

Xavfsizlik qoidalari (Realtime Database > Rules) uchun minimal namuna:

```json
{
  "rules": {
    ".read": false,
    ".write": false
  }
}
```

`firebase-admin` SDK service account orqali ishlagani sababli Admin SDK bu qoidalarni
chetlab o'tadi — bu qoidalar faqat tashqi (mobil/veb) klientlar uchun himoya beradi.

## 3. Render.com'ga deploy qilish

### A. GitHub orqali

1. Loyihani GitHub repozitoriyaga push qiling (`firebase_credentials.json` va `.env`
   fayllarini **hech qachon** commit qilmang — `.gitignore`ga qo'shing).
2. Render.com'da **New > Blueprint** tanlang va repozitoriyani ulang — `render.yaml`
   avtomatik o'qiladi (`Background Worker` turi yaratiladi, chunki bot polling rejimida
   ishlaydi, HTTP port kerak emas).
3. Render dashboard'da quyidagi environment variables'ni qo'lda kiriting:
   - `BOT_TOKEN` — @BotFather'dan olingan token
   - `BOT_USERNAME` — botning username'i (@ belgisisiz)
   - `ADMIN_IDS` — vergul bilan ajratilgan admin Telegram ID'lari
   - `FIREBASE_DB_URL` — Realtime Database URL
   - `FIREBASE_CREDENTIALS_JSON` — service account JSON faylining **to'liq matnini**
     bitta qatorga joylashtirib qo'ying (masalan `cat firebase_credentials.json | jq -c .`
     natijasi)
4. **Deploy** tugmasini bosing. Loglarda "Bot ishga tushmoqda (long polling)..." xabarini
   ko'rsangiz, bot ishga tushgan.

### B. `render.yaml`siz, qo'lda

1. Render dashboard > **New > Background Worker**.
2. Repozitoriyani ulang.
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `python bot.py`
5. Yuqoridagi environment variables'ni qo'shing.

> **Muhim:** Bot polling rejimida ishlagani uchun **Web Service** emas, **Background
> Worker** turi tanlanishi shart — aks holda Render portni kutib, xizmatni "unhealthy"
> deb belgilaydi.

## 4. Admin komandalar

- `/stats` — umumiy statistika (foydalanuvchilar, faol qarzlar, UZS/USD aylanma).
- `/broadcast` — barcha foydalanuvchilarga xabar yuborish (matn kiritilib, tasdiqlangach yuboriladi).

Admin ID'lar `.env` dagi `ADMIN_IDS` orqali beriladi.

## 5. Avtomatik eslatmalar

`services/scheduler.py` har `REMINDER_CHECK_INTERVAL_HOURS` soatda (default: 24) barcha
`status == "active"` qarzlarni tekshiradi. Agar `last_notified_at` dan
`REMINDER_INTERVAL_DAYS` (default: 3) kun o'tgan bo'lsa, qarzdorga o'z tilida eslatma
yuboriladi va `last_notified_at` yangilanadi.
