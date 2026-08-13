import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types


# =========================
# RENDER SERVER
# =========================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        pass


def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


threading.Thread(target=run_server, daemon=True).start()


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.environ["BOT_TOKEN"]

ADMIN_ID = 6189064599

SBER_DETAILS = "2202208584208803 Эрик Ваанович Т."
SBP_DETAILS = "+79935101914 Эрик Ваанович Т."

bot = telebot.TeleBot(BOT_TOKEN)


# =========================
# ЦЕНЫ STARS
# =========================

PRICES = {
    50: 68,
    100: 136,
    150: 204,
    250: 340,
    500: 680,
    1000: 1360
}


# =========================
# PREMIUM
# =========================

PREMIUM_PRICES = {
    3: 1150,
    6: 1550,
    12: 2499
}


# =========================
# ЗАКАЗЫ
# =========================

orders = {}


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "⭐ Купить Stars",
            callback_data="stars"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💎 Купить Telegram Premium",
            callback_data="premium"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💬 Поддержка",
            callback_data="support"
        )
    )

    return markup


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "✨ Добро пожаловать в бота SELL STARS RT!\n\n"
        "⭐ Здесь вы можете купить звёзды "
        "по курсу 1,40 ₽ за 1 шт.\n\n"
        "📦 Минимальный заказ — от 50 Stars.\n"
        "💎 Так же продаётся Telegram Premium.\n\n"
        "Выберите нужный товар:",
        reply_markup=main_menu()
    )


# =========================
# STARS
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
            "✏️ Своё количество",
            callback_data="custom_stars"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back"
        )
    )

    bot.edit_message_text(
        "⭐ Выберите количество Stars:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================
# СВОЁ КОЛИЧЕСТВО
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "custom_stars")
def custom_stars(call):

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "✏️ Напишите количество Stars.\n\n"
        "Минимальный заказ — 50 Stars.\n"
        "Цена — 1,40 ₽ за 1 Star."
    )

    bot.register_next_step_handler(
        call.message,
        process_custom_stars
    )


def process_custom_stars(message):

    try:
        amount = int(message.text.strip())
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Введите количество Stars числом.\n"
            "Например: 250"
        )
        return

    if amount < 50:
        bot.send_message(
            message.chat.id,
            "❌ Минимальный заказ — 50 Stars."
        )
        return

    price = round(amount * 1.40)

    orders[message.from_user.id] = {
        "product": "Stars",
        "amount": amount,
        "price": price
    }

    choose_recipient(message.chat.id, message.from_user.id)


# =========================
# ГОТОВЫЙ ПАКЕТ STARS
# =========================

@bot.callback_query_handler(func=lambda call: call.data.startswith("amount_"))
def choose_amount(call):

    amount = int(call.data.split("_")[1])
    price = PRICES[amount]

    orders[call.from_user.id] = {
        "product": "Stars",
        "amount": amount,
        "price": price
    }

    bot.answer_callback_query(call.id)

    choose_recipient(
        call.message.chat.id,
        call.from_user.id,
        call.message.message_id
    )


# =========================
# ВЫБОР ПОЛУЧАТЕЛЯ STARS
# =========================

def choose_recipient(chat_id, user_id, message_id=None):

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "👤 Себе",
            callback_data="recipient_self"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🎁 Другому",
            callback_data="recipient_other"
        )
    )

    text = (
        f"⭐ Stars: {orders[user_id]['amount']}\n"
        f"💰 Сумма: {orders[user_id]['price']} ₽\n\n"
        "Кому отправить Stars?"
    )

    if message_id:
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            reply_markup=markup
        )
    else:
        bot.send_message(
            chat_id,
            text,
            reply_markup=markup
        )


# =========================
# STARS СЕБЕ
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "recipient_self")
def recipient_self(call):

    user_id = call.from_user.id

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    username = (
        f"@{call.from_user.username}"
        if call.from_user.username
        else f"ID: {user_id}"
    )

    orders[user_id]["recipient"] = username

    bot.answer_callback_query(call.id)

    payment_menu(
        call.message.chat.id,
        call.message.message_id,
        user_id
    )


# =========================
# STARS ДРУГОМУ
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "recipient_other")
def recipient_other(call):

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "👤 Напишите @username пользователя,\n"
        "которому отправить Stars.\n\n"
        "Например: @username"
    )

    bot.register_next_step_handler(
        call.message,
        process_other_recipient
    )


def process_other_recipient(message):

    username = message.text.strip()

    if not username.startswith("@"):
        username = "@" + username

    user_id = message.from_user.id

    if user_id not in orders:
        bot.send_message(
            message.chat.id,
            "❌ Заказ не найден."
        )
        return

    orders[user_id]["recipient"] = username

    payment_menu(
        message.chat.id,
        None,
        user_id
    )


# =========================
# PREMIUM
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "premium")
def premium(call):

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "💎 3 месяца — 1150 ₽",
            callback_data="premium_3"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💎 6 месяцев — 1550 ₽",
            callback_data="premium_6"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💎 12 месяцев — 2499 ₽",
            callback_data="premium_12"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back"
        )
    )

    bot.edit_message_text(
        "💎 Выберите срок Telegram Premium:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================
# ВЫБОР PREMIUM
# =========================

@bot.callback_query_handler(func=lambda call: call.data.startswith("premium_"))
def choose_premium(call):

    months = int(call.data.split("_")[1])
    price = PREMIUM_PRICES[months]

    orders[call.from_user.id] = {
        "product": "Premium",
        "months": months,
        "price": price
    }

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "👤 Себе",
            callback_data="premium_self"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🎁 Другому",
            callback_data="premium_other"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="premium"
        )
    )

    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        f"💎 Telegram Premium — {months} мес.\n"
        f"💰 Сумма: {price} ₽\n\n"
        "Кому оформить Premium?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================
# PREMIUM СЕБЕ
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "premium_self")
def premium_self(call):

    user_id = call.from_user.id

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    username = (
        f"@{call.from_user.username}"
        if call.from_user.username
        else f"ID: {user_id}"
    )

    orders[user_id]["recipient"] = username

    bot.answer_callback_query(call.id)

    payment_menu(
        call.message.chat.id,
        call.message.message_id,
        user_id
    )


# =========================
# PREMIUM ДРУГОМУ
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "premium_other")
def premium_other(call):

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "👤 Напишите @username пользователя,\n"
        "которому оформить Premium.\n\n"
        "Например: @username"
    )

    bot.register_next_step_handler(
        call.message,
        process_premium_other
    )


def process_premium_other(message):

    username = message.text.strip()

    if not username.startswith("@"):
        username = "@" + username

    user_id = message.from_user.id

    if user_id not in orders:
        bot.send_message(
            message.chat.id,
            "❌ Заказ не найден."
        )
        return

    orders[user_id]["recipient"] = username

    payment_menu(
        message.chat.id,
        None,
        user_id
    )


# =========================
# ОПЛАТА
# =========================

def payment_menu(chat_id, message_id, user_id):

    order = orders.get(user_id)

    if not order:
        bot.send_message(
            chat_id,
            "❌ Заказ не найден."
        )
        return

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

    product_text = ""

    if order["product"] == "Stars":
        product_text = (
            f"⭐ Stars: {order['amount']}\n"
            f"🎁 Получатель: {order['recipient']}\n"
        )
    else:
        product_text = (
            f"💎 Premium: {order['months']} мес.\n"
            f"🎁 Получатель: {order['recipient']}\n"
        )

    text = (
        f"{product_text}"
        f"💰 Сумма: {order['price']} ₽\n\n"
        "Выберите способ оплаты:"
    )

    if message_id:
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            reply_markup=markup
        )
    else:
        bot.send_message(
            chat_id,
            text,
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

    orders[call.from_user.id]["payment"] = "Сбербанк"

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data="paid"
        )
    )

    product_text = order_info(order)

    bot.edit_message_text(
        f"🏦 ОПЛАТА СБЕРБАНК\n\n"
        f"{product_text}"
        f"💰 Сумма: {order['price']} ₽\n\n"
        f"Реквизиты:\n"
        f"{SBER_DETAILS}\n\n"
        "После оплаты нажми «Я оплатил» "
        "и отправь чек.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


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

    orders[call.from_user.id]["payment"] = "СБП"

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data="paid"
        )
    )

    product_text = order_info(order)

    bot.edit_message_text(
        f"📱 ОПЛАТА СБП\n\n"
        f"{product_text}"
        f"💰 Сумма: {order['price']} ₽\n\n"
        f"Реквизиты:\n"
        f"{SBP_DETAILS}\n\n"
        "После оплаты нажми «Я оплатил» "
        "и отправь чек.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


def order_info(order):

    if order["product"] == "Stars":
        return (
            f"⭐ Stars: {order['amount']}\n"
            f"🎁 Получатель: {order['recipient']}\n"
        )

    return (
        f"💎 Premium: {order['months']} мес.\n"
        f"🎁 Получатель: {order['recipient']}\n"
    )


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
# ЧЕК
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
        f"{order_info(order)}"
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
# ПОДТВЕРЖДЕНИЕ
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
        f"{order_info(order)}"
        f"💰 Сумма: {order['price']} ₽\n\n"
        "Спасибо за покупку!\n\n"
        "⏳ Заказ будет обработан администратором."
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
        "💬 Если у вас возникли вопросы пишите @Ireqhat4"
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
