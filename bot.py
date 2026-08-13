import telebot
from telebot import types

# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = "8642114423:AAGJQXU3rgvgIoaxYX_E0ZXF0ngTY_AJ7CY"

# Твой Telegram ID
ADMIN_ID = 6189064599

# Реквизиты
SBER_DETAILS = "2202208584208803 Юрий Ваанович Т."
SBP_DETAILS = "+79935101914 Юрий Ваанович Т."

bot = telebot.TeleBot(BOT_TOKEN)

# Цены
PRICES = {
    50: 68,
    100: 136,
    150: 204,
    250: 340,
    500: 680,
    1000: 1360
}

# Запоминаем заказы
orders = {}


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "⭐ Купить Stars",
            callback_data="stars"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💬 Поддержка",
            callback_data="support"
        )
    )

    return markup


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "✨ Добро пожаловать!\n\n"
        "⭐ Здесь можно приобрести Telegram Stars.\n\n"
        "Выбери действие:",
        reply_markup=main_menu()
    )


# =========================
# ВЫБОР STARS
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "stars")
def stars(call):
    markup = types.InlineKeyboardMarkup(row_width=2)

    for amount, price in PRICES.items():
        markup.add(
            types.InlineKeyboardButton(
                f"⭐ {amount} — {price} ₽",
                callback_data=f"amount_{amount}"
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back"
        )
    )

    bot.edit_message_text(
        "⭐ Выбери количество Stars:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================
# ВЫБОР КОЛИЧЕСТВА
# =========================

@bot.callback_query_handler(func=lambda call: call.data.startswith("amount_"))
def choose_amount(call):
    amount = int(call.data.split("_")[1])
    price = PRICES[amount]

    orders[call.from_user.id] = {
        "amount": amount,
        "price": price
    }

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "🏦 Сбербанк",
            callback_data="pay_sber"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "📱 СБП",
            callback_data="pay_sbp"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="stars"
        )
    )

    bot.edit_message_text(
        f"⭐ Заказ: {amount} Stars\n"
        f"💰 Сумма: {price} ₽\n\n"
        f"Выбери способ оплаты:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================
# СБЕРБАНК
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "pay_sber")
def pay_sber(call):

    order = orders.get(call.from_user.id)

    if not order:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data="paid"
        )
    )

    bot.edit_message_text(
        f"🏦 ОПЛАТА СБЕРБАНК\n\n"
        f"⭐ Stars: {order['amount']}\n"
        f"💰 Сумма: {order['price']} ₽\n\n"
        f"Реквизиты:\n"
        f"{SBER_DETAILS}\n\n"
        "После оплаты нажми кнопку «Я оплатил» "
        "и отправь чек.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

    orders[call.from_user.id]["payment"] = "Сбербанк"


# =========================
# СБП
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "pay_sbp")
def pay_sbp(call):

    order = orders.get(call.from_user.id)

    if not order:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data="paid"
        )
    )

    bot.edit_message_text(
        f"📱 ОПЛАТА СБП\n\n"
        f"⭐ Stars: {order['amount']}\n"
        f"💰 Сумма: {order['price']} ₽\n\n"
        f"Реквизиты:\n"
        f"{SBP_DETAILS}\n\n"
        "После оплаты нажми кнопку «Я оплатил» "
        "и отправь чек.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

    orders[call.from_user.id]["payment"] = "СБП"


# =========================
# Я ОПЛАТИЛ
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "paid")
def paid(call):

    if call.from_user.id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    orders[call.from_user.id]["waiting_receipt"] = True

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "📸 Теперь отправь сюда чек или скриншот оплаты.\n\n"
        "После проверки администратор подтвердит заказ."
    )


# =========================
# ПОЛУЧЕНИЕ ФОТО ЧЕКА
# =========================

@bot.message_handler(content_types=["photo"])
def receipt_photo(message):

    user_id = message.from_user.id

    if user_id not in orders:
        bot.reply_to(
            message,
            "❌ Сначала создай заказ через /start."
        )
        return

    order = orders[user_id]

    if not order.get("waiting_receipt"):
        bot.reply_to(
            message,
            "❌ Сначала нажми «Я оплатил»."
        )
        return

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "нет username"
    )

    admin_text = (
        "🧾 НОВЫЙ ЧЕК\n\n"
        f"👤 Покупатель: {username}\n"
        f"🆔 ID: {user_id}\n"
        f"⭐ Stars: {order['amount']}\n"
        f"💰 Сумма: {order['price']} ₽\n"
        f"💳 Оплата: {order.get('payment', 'не указано')}\n"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "✅ Подтвердить",
            callback_data=f"approve_{user_id}"
        ),
        types.InlineKeyboardButton(
            "❌ Отклонить",
            callback_data=f"reject_{user_id}"
        )
    )

    bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=admin_text,
        reply_markup=markup
    )

    bot.reply_to(
        message,
        "✅ Чек отправлен администратору.\n\n"
        "Ожидай проверки оплаты."
    )


# =========================
# ПОДТВЕРЖДЕНИЕ АДМИНОМ
# =========================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("approve_")
)
def approve(call):

    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(
            call.id,
            "⛔ Нет доступа"
        )
        return

    user_id = int(call.data.split("_")[1])

    order = orders.get(user_id)

    if not order:
        bot.answer_callback_query(
            call.id,
            "Заказ уже обработан"
        )
        return

    bot.send_message(
        user_id,
        "✅ ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
        f"⭐ Stars: {order['amount']}\n"
        f"💰 Сумма: {order['price']} ₽\n\n"
        "Спасибо за покупку!"
    )

    bot.answer_callback_query(
        call.id,
        "Заказ подтверждён"
    )

    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None
    )

    del orders[user_id]


# =========================
# ОТКЛОНЕНИЕ
# =========================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("reject_")
)
def reject(call):

    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(
            call.id,
            "⛔ Нет доступа"
        )
        return

    user_id = int(call.data.split("_")[1])

    bot.send_message(
        user_id,
        "❌ Оплата не подтверждена.\n\n"
        "Проверьте чек и обратитесь в поддержку."
    )

    bot.answer_callback_query(
        call.id,
        "Заказ отклонён"
    )

    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None
    )

    if user_id in orders:
        del orders[user_id]


# =========================
# ПОДДЕРЖКА
# =========================

@bot.callback_query_handler(
    func=lambda call: call.data == "support"
)
def support(call):

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "💬 По вопросам заказа обратитесь к администратору."
    )


# =========================
# НАЗАД
# =========================

@bot.callback_query_handler(
    func=lambda call: call.data == "back"
)
def back(call):

    bot.edit_message_text(
        "✨ Главное меню:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_menu()
    )


# =========================
# ЗАПУСК
# =========================

print("🤖 Бот запущен!")

bot.infinity_polling()
