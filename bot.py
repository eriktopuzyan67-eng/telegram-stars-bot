import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types


# =========================================================
# RENDER SERVER
# =========================================================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"SELL STARS RT is running")

    def log_message(self, format, *args):
        pass


def run_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


threading.Thread(
    target=run_server,
    daemon=True
).start()


# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в Render Environment")

ADMIN_ID = 6189064599

SBER_DETAILS = "2202208584208103 Эрик Ваанович Т."
SBP_DETAILS = "2202208584208103 Эрик Ваанович Т."

bot = telebot.TeleBot(BOT_TOKEN)


# =========================================================
# ЦЕНЫ
# =========================================================

STARS_PRICES = {
    50: 68,
    100: 136,
    150: 204,
    250: 340,
    500: 680,
    1000: 1360
}

PREMIUM_PRICES = {
    3: 1150,
    6: 1550,
    12: 2499
}


# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================

USERS_FILE = "users.json"
users = set()


def load_users():
    global users

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            users = set(json.load(file))
    except Exception:
        users = set()


def save_users():
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as file:
            json.dump(list(users), file)
    except Exception as error:
        print("Ошибка сохранения users.json:", error)


def add_user(user_id):
    if user_id not in users:
        users.add(user_id)
        save_users()


load_users()


# =========================================================
# ЗАКАЗЫ
# =========================================================

orders = {}


# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def get_username(user):
    if user.username:
        return "@" + user.username

    return "ID " + str(user.id)


def order_text(order):

    if order["product"] == "Stars":
        product = (
            "⭐ Stars: "
            + str(order["amount"])
        )
    else:
        product = (
            "💎 Premium: "
            + str(order["months"])
            + " месяцев"
        )

    recipient = order.get(
        "recipient",
        "не указан"
    )

    return (
        product
        + "\n🎁 Получатель: "
        + recipient
        + "\n💰 Сумма: "
        + str(order["price"])
        + " ₽"
    )


def main_menu(user_id):

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

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

    if user_id == ADMIN_ID:
        markup.add(
            types.InlineKeyboardButton(
                "📢 Рассылка",
                callback_data="broadcast"
            )
        )

    return markup


def edit_message(call, text, markup):

    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=markup
        )


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    add_user(message.from_user.id)

    text = (
        "👋 Привет, "
        + get_username(message.from_user)
        + "!\n\n"
        "✨ Добро пожаловать в SELL STARS RT!\n\n"
        "⭐ Telegram Stars\n"
        "💎 Telegram Premium\n\n"
        "Выберите нужное действие:"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "stars"
)
def stars(call):

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    for amount, price in STARS_PRICES.items():

        markup.add(
            types.InlineKeyboardButton(
                "⭐ "
                + str(amount)
                + " — "
                + str(price)
                + " ₽",
                callback_data="star_"
                + str(amount)
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
            callback_data="home"
        )
    )

    edit_message(
        call,
        "⭐ Выберите количество Stars:",
        markup
    )


# =========================================================
# ГОТОВЫЕ STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("star_")
)
def choose_stars(call):

    try:
        amount = int(
            call.data.split("_", 1)[1]
        )
    except Exception:
        bot.answer_callback_query(
            call.id,
            "❌ Ошибка"
        )
        return

    if amount not in STARS_PRICES:
        bot.answer_callback_query(
            call.id,
            "❌ Ошибка"
        )
        return

    orders[call.from_user.id] = {
        "product": "Stars",
        "amount": amount,
        "price": STARS_PRICES[amount]
    }

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# СВОЁ КОЛИЧЕСТВО
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "custom_stars"
)
def custom_stars(call):

    bot.answer_callback_query(call.id)

    message = bot.send_message(
        call.message.chat.id,
        "✏️ Напишите количество Stars.\n\n"
        "Минимум — 50 Stars.\n"
        "Цена — 1,40 ₽ за 1 Star."
    )

    bot.register_next_step_handler(
        message,
        custom_stars_amount
    )


def custom_stars_amount(message):

    try:
        amount = int(
            message.text.strip()
        )
    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ Введите количество числом."
        )

        return

    if amount < 50:

        bot.send_message(
            message.chat.id,
            "❌ Минимум — 50 Stars."
        )

        return

    price = round(
        amount * 1.40
    )

    orders[message.from_user.id] = {
        "product": "Stars",
        "amount": amount,
        "price": price
    }

    show_recipient(
        message.chat.id,
        None,
        message.from_user.id
    )


# =========================================================
# PREMIUM
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "premium"
)
def premium(call):

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

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
            callback_data="home"
        )
    )

    edit_message(
        call,
        "💎 Выберите Telegram Premium:",
        markup
    )


@bot.callback_query_handler(
    func=lambda call: call.data in (
        "premium_3",
        "premium_6",
        "premium_12"
    )
)
def choose_premium(call):

    try:
        months = int(
            call.data.split("_", 1)[1]
        )
    except Exception:

        bot.answer_callback_query(
            call.id,
            "❌ Ошибка"
        )

        return

    orders[call.from_user.id] = {
        "product": "Premium",
        "months": months,
        "price": PREMIUM_PRICES[months]
    }

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# ПОЛУЧАТЕЛЬ
# =========================================================

def show_recipient(
    chat_id,
    message_id,
    user_id
):

    order = orders.get(user_id)

    if not order:
        return

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

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

    if order["product"] == "Stars":
        back = "stars"
    else:
        back = "premium"

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data=back
        )
    )

    text = (
        order_text(order)
        + "\n\n"
        "Кому оформить заказ?"
    )

    if message_id is not None:

        try:
            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=markup
            )
        except Exception:

            bot.send_message(
                chat_id,
                text,
                reply_markup=markup
            )

    else:

        bot.send_message(
            chat_id,
            text,
            reply_markup=markup
        )


# =========================================================
# СЕБЕ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "recipient_self"
)
def recipient_self(call):

    user_id = call.from_user.id

    if user_id not in orders:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )

        return

    orders[user_id]["recipient"] = (
        get_username(call.from_user)
    )

    bot.answer_callback_query(call.id)

    show_payment(
        call.message.chat.id,
        call.message.message_id,
        user_id
    )


# =========================================================
# ДРУГОМУ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "recipient_other"
)
def recipient_other(call):

    bot.answer_callback_query(call.id)

    message = bot.send_message(
        call.message.chat.id,
        "👤 Напишите @username пользователя."
    )

    bot.register_next_step_handler(
        message,
        save_recipient
    )


def save_recipient(message):

    if not message.text:

        bot.send_message(
            message.chat.id,
            "❌ Введите @username."
        )

        return

    recipient = message.text.strip()

    if not recipient.startswith("@"):
        recipient = "@" + recipient

    user_id = message.from_user.id

    if user_id not in orders:

        bot.send_message(
            message.chat.id,
            "❌ Заказ не найден."
        )

        return

    orders[user_id]["recipient"] = recipient

    show_payment(
        message.chat.id,
        None,
        user_id
    )


# =========================================================
# ОПЛАТА
# =========================================================

def show_payment(
    chat_id,
    message_id,
    user_id
):

    order = orders.get(user_id)

    if not order:
        return

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

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
            callback_data="payment_back"
        )
    )

    text = (
        order_text(order)
        + "\n\n"
        "💳 Выберите способ оплаты:"
    )

    if message_id is not None:

        try:
            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=markup
            )
        except Exception:

            bot.send_message(
                chat_id,
                text,
                reply_markup=markup
            )

    else:

        bot.send_message(
            chat_id,
            text,
            reply_markup=markup
        )


# =========================================================
# СБЕРБАНК
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "pay_sber"
)
def pay_sber(call):

    user_id = call.from_user.id

    if user_id not in orders:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )

        return

    order = orders[user_id]
    order["payment"] = "Сбербанк"

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    markup.add(
        types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data="paid"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="payment_back"
        )
    )

    text = (
        "🏦 ОПЛАТА СБЕРБАНК\n\n"
        + order_text(order)
        + "\n\n"
        "💳 Реквизиты:\n"
        + SBER_DETAILS
        + "\n\n"
        "После оплаты нажмите «Я оплатил» "
        "и отправьте чек."
    )

    bot.answer_callback_query(call.id)

    edit_message(
        call,
        text,
        markup
    )


# =========================================================
# СБП
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "pay_sbp"
)
def pay_sbp(call):

    user_id = call.from_user.id

    if user_id not in orders:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )

        return

    order = orders[user_id]
    order["payment"] = "СБП"

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    markup.add(
        types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data="paid"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="payment_back"
        )
    )

    text = (
        "📱 ОПЛАТА СБП\n\n"
        + order_text(order)
        + "\n\n"
        "💳 Реквизиты:\n"
        + SBP_DETAILS
        + "\n\n"
        "После оплаты нажмите «Я оплатил» "
        "и отправьте чек."
    )

    bot.answer_callback_query(call.id)

    edit_message(
        call,
        text,
        markup
    )


# =========================================================
# НАЗАД ОТ ОПЛАТЫ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "payment_back"
)
def payment_back(call):

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# Я ОПЛАТИЛ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "paid"
)
def paid(call):

    user_id = call.from_user.id

    if user_id not in orders:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )

        return

    orders[user_id]["waiting_receipt"] = True

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "📸 Теперь отправьте сюда чек "
        "или скриншот оплаты."
    )


# =========================================================
# ПОЛУЧЕНИЕ ЧЕКА
# =========================================================

@bot.message_handler(
    content_types=["photo"]
)
def receipt_photo(message):

    user_id = message.from_user.id

    if user_id not in orders:

        bot.reply_to(
            message,
            "❌ Сначала создайте заказ через /start."
        )

        return

    order = orders[user_id]

    if not order.get("waiting_receipt"):

        bot.reply_to(
            message,
            "❌ Сначала нажмите «Я оплатил»."
        )

        return

    order["waiting_receipt"] = False

    admin_text = (
        "🧾 НОВЫЙ ЧЕК\n\n"
        "👤 Покупатель: "
        + get_username(message.from_user)
        + "\n"
        "🆔 ID: "
        + str(user_id)
        + "\n\n"
        + order_text(order)
        + "\n"
        "💳 Оплата: "
        + order.get(
            "payment",
            "не указано"
        )
    )

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "✅ Подтвердить",
            callback_data="approve_"
            + str(user_id)
        ),
        types.InlineKeyboardButton(
            "❌ Отклонить",
            callback_data="reject_"
            + str(user_id)
        )
    )

    try:

        bot.send_photo(
            ADMIN_ID,
            message.photo[-1].file_id,
            caption=admin_text,
            reply_markup=markup
        )

        bot.reply_to(
            message,
            "✅ Чек отправлен администратору!\n\n"
            "⏳ Ожидайте проверки."
        )

    except Exception as error:

        print(
            "Ошибка отправки чека:",
            error
        )

        bot.reply_to(
            message,
            "❌ Не удалось отправить чек."
        )


# =========================================================
# АДМИН — ПОДТВЕРДИТЬ
# =========================================================

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

    try:
        user_id = int(
            call.data.split("_", 1)[1]
        )
    except (ValueError, IndexError):
        bot.answer_callback_query(
            call.id,
            "❌ Ошибка ID"
        )
        return

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )
        return

    order = orders[user_id]
    order["confirmed"] = True

    bot.answer_callback_query(
        call.id,
        "✅ Оплата подтверждена"
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "📦 Заказ выполнен",
            callback_data="done_" + str(user_id)
        )
    )

    try:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        pass

    bot.send_message(
        user_id,
        "✅ ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
        + order_text(order)
        + "\n\n"
        "📦 Заказ передан в обработку."
    )


# =========================================================
# АДМИН — ОТКЛОНИТЬ
# =========================================================

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

    try:
        user_id = int(
            call.data.split("_", 1)[1]
        )
    except (ValueError, IndexError):
        bot.answer_callback_query(
            call.id,
            "❌ Ошибка ID"
        )
        return

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )
        return

    bot.answer_callback_query(
        call.id,
        "❌ Чек отклонён"
    )

    bot.send_message(
        user_id,
        "❌ Ваш платёж не был подтверждён.\n\n"
        "Обратитесь в поддержку."
    )


# =========================================================
# АДМИН — ЗАКАЗ ВЫПОЛНЕН
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("done_")
)
def done(call):

    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(
            call.id,
            "⛔ Нет доступа"
        )
        return

    try:
        user_id = int(
            call.data.split("_", 1)[1]
        )
    except (ValueError, IndexError):
        bot.answer_callback_query(
            call.id,
            "❌ Ошибка ID"
        )
        return

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )
        return

    order = orders[user_id]
    order["completed"] = True

    bot.answer_callback_query(
        call.id,
        "📦 Заказ выполнен"
    )

    bot.send_message(
        user_id,
        "🎉 ЗАКАЗ ВЫПОЛНЕН!\n\n"
        + order_text(order)
        + "\n\n"
        "Спасибо за покупку ❤️"
    )


# =========================================================
# ПОДДЕРЖКА
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "support"
)
def support(call):

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
    )

    edit_message(
        call,
        "💬 ПОДДЕРЖКА\n\n"
        "Если у вас проблема с заказом, "
        "обратитесь к администратору.\n\n"
        "🆔 Ваш ID: "
        + str(call.from_user.id),
        markup
    )


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "home"
)
def home(call):

    bot.answer_callback_query(call.id)

    edit_message(
        call,
        "🏠 Главное меню:",
        main_menu(call.from_user.id)
    )


# =========================================================
# РАССЫЛКА
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "broadcast"
)
def broadcast(call):

    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(
            call.id,
            "⛔ Нет доступа"
        )
        return

    bot.answer_callback_query(call.id)

    message = bot.send_message(
        call.message.chat.id,
        "📢 Напишите текст рассылки:"
    )

    bot.register_next_step_handler(
        message,
        broadcast_send
    )


def broadcast_send(message):

    if message.from_user.id != ADMIN_ID:
        return

    if not message.text:
        bot.send_message(
            message.chat.id,
            "❌ Нужен текст."
        )
        return

    success = 0
    failed = 0

    for user_id in list(users):
        try:
            bot.send_message(
                user_id,
                message.text
            )
            success += 1
        except Exception as error:
            failed += 1
            print(
                "Ошибка рассылки:",
                user_id,
                error
            )

    bot.send_message(
        message.chat.id,
        "📢 Рассылка завершена!\n\n"
        "✅ Отправлено: "
        + str(success)
        + "\n"
        "❌ Ошибок: "
        + str(failed)
    )


# =========================================================
# ОБЫЧНЫЙ ТЕКСТ
# =========================================================

@bot.message_handler(
    content_types=["text"]
)
def text_handler(message):

    add_user(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "🏠 Используйте меню:",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# ЗАПУСК
# =========================================================

print("SELL STARS RT: BOT STARTING")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
    )
