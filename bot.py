import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types


# =========================================================
# RENDER WEB SERVER
# =========================================================

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"SELL STARS RT is running")

    def log_message(self, format, *args):
        pass


def run_server():
    port = int(os.environ.get("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print("Web server started on port", port)

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
    raise RuntimeError(
        "BOT_TOKEN не найден в Environment Variables"
    )


ADMIN_ID = 6189064599


# Эти две переменные можно добавить в Render.
# Если их нет, будут использованы значения ниже.

SBER_DETAILS = os.environ.get(
    "SBER_DETAILS",
    "Укажите реквизиты Сбербанка"
)

SBP_DETAILS = os.environ.get(
    "SBP_DETAILS",
    "Укажите реквизиты СБП"
)


bot = telebot.TeleBot(BOT_TOKEN)


# =========================================================
# ЦЕНЫ STARS
# =========================================================

PRICES = {
    50: 68,
    100: 136,
    150: 204,
    250: 340,
    500: 680,
    1000: 1360
}


# =========================================================
# ЦЕНЫ PREMIUM
# =========================================================

PREMIUM_PRICES = {
    3: 1150,
    6: 1550,
    12: 2499
}


# =========================================================
# ЗАКАЗЫ
# =========================================================

orders = {}


# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================

USERS_FILE = "users.json"


def load_users():

    try:
        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            return set(data)

    except Exception:
        return set()


users = load_users()


def save_users():

    try:

        with open(
            USERS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                list(users),
                file,
                ensure_ascii=False
            )

    except Exception as error:

        print(
            "Ошибка сохранения users.json:",
            error
        )


def register_user(user_id):

    if user_id not in users:

        users.add(user_id)

        save_users()


# =========================================================
# USERNAME
# =========================================================

def get_username(user):

    if user.username:

        return "@" + user.username

    return "ID " + str(user.id)


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

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


# =========================================================
# ОПИСАНИЕ ЗАКАЗА
# =========================================================

def order_description(order):

    if order["product"] == "Stars":

        return (
            f"⭐ Stars: {order['amount']}\n"
            f"🎁 Получатель: "
            f"{order.get('recipient', 'не указан')}\n"
        )

    return (
        f"💎 Premium: "
        f"{order['months']} мес.\n"
        f"🎁 Получатель: "
        f"{order.get('recipient', 'не указан')}\n"
    )


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    register_user(
        message.from_user.id
    )

    username = get_username(
        message.from_user
    )

    text = (
        f"👋 Приветствую, {username}!\n\n"
        "✨ Добро пожаловать в "
        "SELL STARS RT!\n\n"
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

    register_user(
        call.from_user.id
    )

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

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

    bot.answer_callback_query(
        call.id
    )

    bot.edit_message_text(
        "⭐ Выберите количество Stars:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# ГОТОВОЕ КОЛИЧЕСТВО STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("amount_")
)
def choose_amount(call):

    try:

        amount = int(
            call.data.split(
                "_",
                1
            )[1]
        )

    except Exception:

        bot.answer_callback_query(
            call.id,
            "Ошибка количества"
        )

        return

    if amount not in PRICES:

        bot.answer_callback_query(
            call.id,
            "Такого количества нет"
        )

        return

    orders[call.from_user.id] = {
        "product": "Stars",
        "amount": amount,
        "price": PRICES[amount]
    }

    bot.answer_callback_query(
        call.id
    )

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

    bot.answer_callback_query(
        call.id
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="stars"
        )
    )

    message = bot.send_message(
        call.message.chat.id,
        "✏️ Напишите количество Stars.\n\n"
        "Минимум: 50 Stars\n"
        "Цена: 1,40 ₽ за 1 Star.",
        reply_markup=markup
    )

    bot.register_next_step_handler(
        message,
        custom_stars_amount
    )


def custom_stars_amount(message):

    register_user(
        message.from_user.id
    )

    if not message.text:

        bot.send_message(
            message.chat.id,
            "❌ Введите число."
        )

        return

    try:

        amount = int(
            message.text.strip()
        )

    except ValueError:

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
            callback_data="back"
        )
    )

    bot.answer_callback_query(
        call.id
    )

    bot.edit_message_text(
        "💎 Выберите срок Telegram Premium:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# ВЫБОР PREMIUM
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data in (
        "premium_3",
        "premium_6",
        "premium_12"
    )
)
def choose_premium(call):

    months = int(
        call.data.split(
            "_",
            1
        )[1]
    )

    orders[call.from_user.id] = {
        "product": "Premium",
        "months": months,
        "price": PREMIUM_PRICES[months]
    }

    bot.answer_callback_query(
        call.id
    )

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

    order = orders.get(
        user_id
    )

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

        back_callback = "stars"

    else:

        back_callback = "premium"

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data=back_callback
        )
    )

    text = (
        order_description(order)
        + f"💰 Сумма: "
        f"{order['price']} ₽\n\n"
        "Кому оформить заказ?"
    )

    if message_id is not None:

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
            "Заказ не найден"
        )

        return

    orders[user_id]["recipient"] = (
        get_username(
            call.from_user
        )
    )

    bot.answer_callback_query(
        call.id
    )

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

    bot.answer_callback_query(
        call.id
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="recipient_back"
        )
    )

    message = bot.send_message(
        call.message.chat.id,
        "👤 Напишите @username пользователя:",
        reply_markup=markup
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
# НАЗАД ОТ ПОЛУЧАТЕЛЯ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "recipient_back"
)
def recipient_back(call):

    bot.answer_callback_query(
        call.id
    )

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# ОПЛАТА
# =========================================================

def show_payment(
    chat_id,
    message_id,
    user_id
):

    order = orders.get(
        user_id
    )

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
        order_description(order)
        + f"💰 Сумма: "
        f"{order['price']} ₽\n\n"
        "Выберите способ оплаты:"
    )

    if message_id is not None:

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


# =========================================================
# СБЕРБАНК
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "pay_sber"
)
def pay_sber(call):

    user_id = call.from_user.id

    order = orders.get(
        user_id
    )

    if not order:

        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )

        return

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

    bot.answer_callback_query(
        call.id
    )

    text = (
        "🏦 ОПЛАТА СБЕРБАНК\n\n"
        + order_description(order)
        + f"💰 Сумма: "
        f"{order['price']} ₽\n\n"
        + "Реквизиты:\n"
        + SBER_DETAILS
        + "\n\n"
        "После оплаты нажмите "
        "«Я оплатил» и отправьте чек."
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# СБП
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "pay_sbp"
)
def pay_sbp(call):

    user_id = call.from_user.id

    order = orders.get(
        user_id
    )

    if not order:

        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )

        return

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

    bot.answer_callback_query(
        call.id
    )

    text = (
        "📱 ОПЛАТА СБП\n\n"
        + order_description(order)
        + f"💰 Сумма: "
        f"{order['price']} ₽\n\n"
        + "Реквизиты:\n"
        + SBP_DETAILS
        + "\n\n"
        "После оплаты нажмите "
        "«Я оплатил» и отправьте чек."
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# НАЗАД ОТ ОПЛАТЫ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "payment_back"
)
def payment_back(call):

    bot.answer_callback_query(
        call.id
    )

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
            "Заказ не найден"
        )

        return

    order = orders[user_id]

    if "payment" not in order:

        bot.answer_callback_query(
            call.id,
            "Сначала выберите способ оплаты"
        )

        return

    order["waiting_receipt"] = True

    bot.answer_callback_query(
        call.id
    )

    bot.send_message(
        call.message.chat.id,
        "📸 Отправьте сюда чек "
        "или скриншот оплаты.\n\n"
        "⏳ После этого администратор "
        "проверит платёж."
    )


# =========================================================
# ПОЛУЧЕНИЕ ЧЕКА
# =========================================================

@bot.message_handler(
    content_types=["photo"]
)
def receipt_photo(message):

    user_id = message.from_user.id

    register_user(
        user_id
    )

    if user_id not in orders:

        bot.reply_to(
            message,
            "❌ Сначала создайте заказ."
        )

        return

    order = orders[user_id]

    if not order.get(
        "waiting_receipt",
        False
    ):

        bot.reply_to(
            message,
   
