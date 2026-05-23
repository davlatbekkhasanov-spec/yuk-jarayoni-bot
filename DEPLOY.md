# Deploy (Railway)

## Majburiy Variables

| O‘zgaruvchi | Misol |
|-------------|--------|
| `BOT_TOKEN` | @BotFather |
| `ADMIN_ID` | `123456789` |
| `GROUP_ID` | `-1001234567890` (guruhda `/id`) |

## Mas'ullar deploydan keyin yo‘qolmasin

**Muammo:** Deployda SQLite yangi bo‘lsa, bot ichida qo‘shilgan mas'ullar o‘chadi.

**Yechim 1 (tavsiya):** Railway → Variables:

```env
MASUL_IDS=111111111,222222222,333333333
```

Vergul bilan — **har deployda avtomatik** qayta yoziladi.  
Menga yuborish shart emas; xavfsizroq — faqat Railway da saqlang.

**Yechim 2:** **Volume** ulang (bot orqali qo‘shilganlar ham saqlanadi):

1. Railway → Service → **Volumes** → Add Volume  
2. Mount path: `/app` yoki loyiha papkasi  
3. `DB_PATH=yuk_bot.db` (fayl volume ichida qoladi)

Ikkalasini birga ishlatish mumkin: `MASUL_IDS` + Volume.

## Start

- Command: `python bot.py`
- Guruhda bot **admin**
- Shaxsiy chatda `/guruh` — GROUP_ID tekshiruvi
