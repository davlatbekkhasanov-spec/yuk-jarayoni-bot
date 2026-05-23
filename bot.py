from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import os

# TOKEN Railway Variables дан олинади
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# START LOAD
@dp.message(Command("startload"))
async def start_load(message: types.Message):

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

    await message.answer(
        "🚚 Юк келди\n\n"
        "📸 Машина фото юборинг",
        reply_markup=kb
    )


# JOIN BUTTON
@dp.callback_query()
async def join_handler(callback: types.CallbackQuery):

    user = callback.from_user.full_name

    await callback.message.answer(
        f"✅ {user} қатнашди"
    )

    await callback.answer()


# GROUP ID
@dp.message(Command("id"))
async def get_group_id(message: types.Message):

    await message.answer(
        f"📌 Group ID:\n{message.chat.id}"
    )


# MAIN
async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
