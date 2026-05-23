from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ACTIVE LOAD
active_users = []


# START
@dp.message(Command("start"))
async def start(message: types.Message):

    await message.answer(
        "✅ Bot ishlayapti.\n\n"
        "/id - chat id\n"
        "/startload - yuk boshlash"
    )


# GROUP ID
@dp.message(Command("id"))
async def get_id(message: types.Message):

    await message.answer(
        f"📌 Chat ID:\n{message.chat.id}"
    )


# START LOAD
@dp.message(Command("startload"))
async def start_load(message: types.Message):

    global active_users
    active_users = []

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Қатнашиш",
                    callback_data="join_load"
                )
            ]
        ]
    )

    text = (
        "🚚 ЮК КЕЛДИ\n\n"
        "📸 Машина фото юборинг\n\n"
        "👷 Қатнашувчилар:\n"
        "Ҳозирча йўқ"
    )

    await message.answer(
        text,
        reply_markup=kb
    )


# JOIN
@dp.callback_query()
async def join_handler(callback: types.CallbackQuery):

    global active_users

    user = callback.from_user.full_name

    if user not in active_users:
        active_users.append(user)

    users_text = "\n".join(
        [f"{i+1}. {name}" for i, name in enumerate(active_users)]
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Қатнашиш",
                    callback_data="join_load"
                )
            ]
        ]
    )

    text = (
        "🚚 ЮК КЕЛДИ\n\n"
        "📸 Машина фото юборинг\n\n"
        "👷 Қатнашувчилар:\n"
        f"{users_text}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb
    )

    await callback.answer("Сиз қатнашдингиз ✅")


# MAIN
async def main():

    print("Bot ishga tushdi...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
