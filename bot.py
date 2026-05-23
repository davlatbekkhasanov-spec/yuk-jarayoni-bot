from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "✅ Bot ishlayapti.\n\n"
        "Buyruqlar:\n"
        "/id - chat ID olish\n"
        "/startload - yuk jarayonini boshlash"
    )


@dp.message(Command("id"))
async def get_id(message: types.Message):
    await message.answer(f"📌 Chat ID:\n{message.chat.id}")


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


@dp.callback_query()
async def join_handler(callback: types.CallbackQuery):
    user = callback.from_user.full_name
    await callback.message.answer(f"✅ {user} қатнашди")
    await callback.answer()


async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
