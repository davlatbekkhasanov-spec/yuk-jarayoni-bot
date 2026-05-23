# 🚚 Юк жараёни боти

Telegram bot — yuk kelishi, qatnashuvchilar, live tаймер va avtomatik otchot.

## Oqim

1. **Mas'ul** (shaxsiy chat): `🚚 Юк келди` → mashina → **қўшимча расм**  
2. **Guruh**: albom + `✅ Қатнашиш`  
3. **Ishchilar**: tugma → shaxsiy chatda tаймер  
4. **Mas'ul**: `🏁 Якунлаш` → 2 ta oxirgi foto → **отчёт** guruhga  

## Sozlash

```bash
cp env.example .env
# BOT_TOKEN, ADMIN_ID, GROUP_ID to'ldiring
pip install -r requirements.txt
python bot.py
```

Guruhda bot **admin** bo‘lishi kerak (xabarlarni tahrirlash uchun).

### Ko‘p mas'ul (Railway shart emas)

Asosiy admin: `➕ Масъул қўшиш` — ID forward/reply.  
Ularda `🚚 Юк келди` va `🏁 Якунлаш` ochiladi.

## Fayl tuzilmasi

- `handlers/` — mas'ul va guruh  
- `ui.py` — professional HTML kartalar  
- `services/ticker.py` — live tаймер (har 5 s)  
- `db.py` — SQLite sessiyalar  

Repo: https://github.com/davlatbekkhasanov-spec/yuk-jarayoni-bot
