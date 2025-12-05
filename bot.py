import telebot
from telebot import types
import os
from dotenv import load_dotenv
from database import DatabaseManager
from current_api import convert_currency, get_all_supported_currencies
import re

load_dotenv()

# Инициализация бота и базы данных
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
db = DatabaseManager()

# Словарь для хранения временных данных пользователей
user_states = {}

# Кэш для списка валют
available_currencies = {}

# Популярные страны/регионы с их валютами (для быстрого выбора)
POPULAR_COUNTRIES = {
    'Россия': 'RUB',
    'США': 'USD',
    'Китай': 'CNY',
    'Япония': 'JPY',
    'Великобритания': 'GBP',
    'Евросоюз': 'EUR',
    'Германия': 'EUR',
    'Франция': 'EUR',
    'Испания': 'EUR',
    'Италия': 'EUR',
    'Южная Корея': 'KRW',
    'Индия': 'INR',
    'Бразилия': 'BRL',
    'Мексика': 'MXN',
    'Аргентина': 'ARS',
    'Чили': 'CLP',
    'Колумбия': 'COP',
    'Перу': 'PEN',
    'Вьетнам': 'VND',
    'ЮАР': 'ZAR',
    'Турция': 'TRY',
    'Украина': 'UAH',
    'Казахстан': 'KZT',
    'Киргизия': 'KGS',
    'Беларусь': 'BYN',
    'Армения': 'AMD',
    'Азербайджан': 'AZN',
    'Таиланд': 'THB',
    'Индонезия': 'IDR',
    'Малайзия': 'MYR',
    'Сингапур': 'SGD',
    'Вьетнам': 'VND',
    'Филиппины': 'PHP',
    'Австралия': 'AUD',
    'Новая Зеландия': 'NZD',
    'Канада': 'CAD',
    'Швейцария': 'CHF',
    'Швеция': 'SEK',
    'Норвегия': 'NOK',
    'Дания': 'DKK',
    'Польша': 'PLN',
    'Чехия': 'CZK',
    'Венгрия': 'HUF',
    'Румыния': 'RON',
    'Болгария': 'BGN',
    'Израиль': 'ILS',
    'ОАЭ': 'AED',
    'Саудовская Аравия': 'SAR',
    'Египет': 'EGP',
    'Марокко': 'MAD',
    'Тунис': 'TND',
}


def load_available_currencies():
    """Загрузить список доступных валют из API"""
    global available_currencies
    try:
        result = get_all_supported_currencies()
        if result.get('success'):
            available_currencies = result.get('currencies', {})
            return True
    except Exception as e:
        print(f"Ошибка при загрузке валют: {e}")
    return False


def get_currency_name(code: str) -> str:
    """Получить название валюты по коду"""
    if code in available_currencies:
        return available_currencies[code]
    return code


def get_main_menu_keyboard():
    """Создать главное меню с inline-кнопками"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("✈️ Создать путешествие", callback_data="menu_new_trip"),
        types.InlineKeyboardButton("🗂 Мои путешествия", callback_data="menu_my_trips"),
        types.InlineKeyboardButton("💰 Баланс", callback_data="menu_balance"),
        types.InlineKeyboardButton("📊 История расходов", callback_data="menu_history"),
        types.InlineKeyboardButton("💱 Изменить курс", callback_data="menu_change_rate"),
        types.InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help")
    )
    return keyboard


def format_number(num: float) -> str:
    """Форматировать число с разделением тысяч"""
    return f"{num:,.2f}".replace(",", " ")


@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Добавить пользователя в базу данных
    db.add_user(user_id, username)
    
    # Загрузить список валют из API, если ещё не загружен
    if not available_currencies:
        load_available_currencies()
    
    welcome_text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я — твой личный помощник для управления финансами в путешествиях! 🌍\n\n"
        "Со мной ты сможешь:\n"
        "• Создавать кошельки для разных путешествий\n"
        "• Отслеживать расходы в разных валютах\n"
        "• Видеть актуальные курсы обмена\n"
        "• Вести историю всех трат\n\n"
        f"💱 Поддерживается {len(available_currencies) if available_currencies else '150+'} валют из всех стран мира!\n\n"
        "Выбери действие из меню ниже 👇"
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu_keyboard())


@bot.message_handler(commands=['menu'])
def menu_command(message):
    """Показать главное меню"""
    bot.send_message(
        message.chat.id,
        "📱 Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data == "menu_new_trip")
def callback_new_trip(call):
    """Начать создание нового путешествия"""
    user_id = call.from_user.id
    user_states[user_id] = {'state': 'waiting_currency_from'}
    
    # Показать популярные страны
    popular_list = "\n".join([f"• {country} ({currency})" for country, currency in sorted(POPULAR_COUNTRIES.items())])
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=(
            "✈️ Создание нового путешествия\n\n"
            "Шаг 1/5: Выберите валюту отправления\n\n"
            "Вы можете:\n"
            "1️⃣ Написать название страны из списка ниже\n"
            "2️⃣ Написать код валюты напрямую (например: RUB, USD, EUR)\n\n"
            "📍 Популярные направления:\n" + popular_list + "\n\n"
            "💡 Поддерживаются все мировые валюты!"
        )
    )


@bot.callback_query_handler(func=lambda call: call.data == "menu_my_trips")
def callback_my_trips(call):
    """Показать все путешествия пользователя"""
    user_id = call.from_user.id
    trips = db.get_all_trips(user_id)
    
    if not trips:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="У вас пока нет путешествий. Создайте первое! 🌍",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for trip in trips:
        status = "✅" if trip['is_active'] else "⭕️"
        button_text = f"{status} {trip['trip_name']} ({trip['currency_from']} → {trip['currency_to']})"
        keyboard.add(
            types.InlineKeyboardButton(
                button_text,
                callback_data=f"switch_trip_{trip['trip_id']}"
            )
        )
    keyboard.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🗂 Ваши путешествия:\n\nНажмите на путешествие, чтобы сделать его активным:",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("switch_trip_"))
def callback_switch_trip(call):
    """Переключить активное путешествие"""
    user_id = call.from_user.id
    trip_id = int(call.data.split("_")[2])
    
    if db.switch_active_trip(user_id, trip_id):
        trip = db.get_active_trip(user_id)
        bot.answer_callback_query(call.id, "✅ Путешествие активировано!")
        
        text = (
            f"✅ Активировано путешествие: {trip['trip_name']}\n\n"
            f"📍 Маршрут: {trip['country_from']} → {trip['country_to']}\n"
            f"💱 Курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}\n"
            f"💰 Баланс: {format_number(trip['balance_to'])} {trip['currency_to']} "
            f"= {format_number(trip['balance_from'])} {trip['currency_from']}"
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=get_main_menu_keyboard()
        )
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка при переключении")


@bot.callback_query_handler(func=lambda call: call.data == "menu_balance")
def callback_balance(call):
    """Показать баланс активного путешествия"""
    user_id = call.from_user.id
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="У вас нет активного путешествия. Создайте новое! 🌍",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    stats = db.get_trip_statistics(trip['trip_id'])
    
    text = (
        f"💰 Баланс путешествия: {trip['trip_name']}\n\n"
        f"📍 Маршрут: {trip['country_from']} → {trip['country_to']}\n"
        f"💱 Текущий курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}\n\n"
        f"💵 Текущий баланс:\n"
        f"  • {format_number(trip['balance_to'])} {trip['currency_to']}\n"
        f"  • {format_number(trip['balance_from'])} {trip['currency_from']}\n\n"
        f"📊 Статистика:\n"
        f"  • Начальная сумма: {format_number(trip['initial_amount_from'])} {trip['currency_from']}\n"
        f"  • Потрачено: {format_number(stats['total_spent_from'])} {trip['currency_from']}\n"
        f"  • Количество расходов: {stats['total_expenses']}"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "menu_history")
def callback_history(call):
    """Показать историю расходов"""
    user_id = call.from_user.id
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="У вас нет активного путешествия.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    expenses = db.get_trip_expenses(trip['trip_id'], limit=15)
    
    if not expenses:
        text = f"📊 История расходов: {trip['trip_name']}\n\nПока нет записей о расходах."
    else:
        text = f"📊 История расходов: {trip['trip_name']}\n\n"
        for exp in expenses:
            date_str = exp['created_at'].split()[0] if ' ' in exp['created_at'] else exp['created_at']
            text += (
                f"📅 {date_str}\n"
                f"  💸 {format_number(exp['amount_to'])} {trip['currency_to']} "
                f"= {format_number(exp['amount_from'])} {trip['currency_from']}\n\n"
            )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "menu_change_rate")
def callback_change_rate(call):
    """Изменить курс обмена"""
    user_id = call.from_user.id
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="У вас нет активного путешествия.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    user_states[user_id] = {
        'state': 'waiting_new_rate',
        'trip_id': trip['trip_id'],
        'message_id': call.message.message_id
    }
    
    text = (
        f"💱 Изменение курса для путешествия: {trip['trip_name']}\n\n"
        f"Текущий курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}\n\n"
        f"Введите новый курс обмена (например, {trip['exchange_rate']:.4f}):"
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text
    )


@bot.callback_query_handler(func=lambda call: call.data == "menu_help")
def callback_help(call):
    """Показать справку"""
    currency_count = len(available_currencies) if available_currencies else "150+"
    help_text = (
        "ℹ️ Справка по использованию бота\n\n"
        "🔹 Создание путешествия:\n"
        "Нажмите 'Создать путешествие' и следуйте инструкциям. "
        "Вы можете написать название страны (Россия, США) или код валюты (RUB, USD). "
        f"Поддерживаются {currency_count} валют из всех стран мира! "
        "Начальная сумма автоматически конвертируется по текущему курсу.\n\n"
        "🔹 Учёт расходов:\n"
        "Просто отправьте число — бот воспримет его как расход "
        "в валюте страны пребывания и предложит подтвердить.\n\n"
        "🔹 Переключение путешествий:\n"
        "Через меню 'Мои путешествия' вы можете переключаться между "
        "разными поездками.\n\n"
        "🔹 Команды:\n"
        "/start — запустить бота\n"
        "/menu — показать главное меню\n"
        "/newtrip — создать новое путешествие\n"
        "/balance — показать баланс\n"
        "/history — история расходов\n"
        "/setrate — изменить курс обмена\n"
        "/switch — переключить путешествие"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=help_text,
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def callback_back_to_menu(call):
    """Вернуться в главное меню"""
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📱 Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_expense_"))
def callback_confirm_expense(call):
    """Подтверждение добавления расхода"""
    user_id = call.from_user.id
    action = call.data.split("_")[2]  # yes или no
    
    if action == "yes":
        if user_id in user_states and 'pending_expense' in user_states[user_id]:
            expense_data = user_states[user_id]['pending_expense']
            trip = db.get_active_trip(user_id)
            
            if trip:
                db.add_expense(
                    trip['trip_id'],
                    expense_data['amount_to'],
                    expense_data['amount_from']
                )
                
                # Получить обновлённый баланс
                trip = db.get_active_trip(user_id)
                
                text = (
                    f"✅ Расход учтён!\n\n"
                    f"💸 Потрачено: {format_number(expense_data['amount_to'])} {trip['currency_to']} "
                    f"= {format_number(expense_data['amount_from'])} {trip['currency_from']}\n\n"
                    f"💰 Остаток: {format_number(trip['balance_to'])} {trip['currency_to']} "
                    f"= {format_number(trip['balance_from'])} {trip['currency_from']}"
                )
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=text
                )
                
                # Очистить временные данные
                if 'pending_expense' in user_states[user_id]:
                    del user_states[user_id]['pending_expense']
            else:
                bot.answer_callback_query(call.id, "❌ Нет активного путешествия")
        else:
            bot.answer_callback_query(call.id, "❌ Данные устарели")
    else:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="❌ Расход не учтён."
        )
        if user_id in user_states and 'pending_expense' in user_states[user_id]:
            del user_states[user_id]['pending_expense']


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_rate_"))
def callback_confirm_rate(call):
    """Подтверждение использования курса API"""
    user_id = call.from_user.id
    action = call.data.split("_")[2]  # yes или no
    
    if user_id not in user_states or 'trip_creation' not in user_states[user_id]:
        bot.answer_callback_query(call.id, "❌ Данные устарели")
        return
    
    trip_data = user_states[user_id]['trip_creation']
    
    if action == "yes":
        # Использовать курс API
        user_states[user_id]['state'] = 'waiting_initial_amount'
        user_states[user_id]['trip_creation']['exchange_rate'] = trip_data['api_rate']
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"✅ Отлично! Курс принят.\n\n"
                f"Шаг 5/5: Введите начальную сумму в {trip_data['currency_from']}, "
                f"которую вы берёте с собой в путешествие:"
            )
        )
    else:
        # Запросить ручной ввод курса
        user_states[user_id]['state'] = 'waiting_manual_rate'
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"Введите курс обмена вручную.\n\n"
                f"Формат: 1 {trip_data['currency_from']} = ? {trip_data['currency_to']}\n"
                f"Например: {trip_data['api_rate']:.4f}"
            )
        )


@bot.message_handler(commands=['newtrip'])
def newtrip_command(message):
    """Команда для создания нового путешествия"""
    user_id = message.from_user.id
    user_states[user_id] = {'state': 'waiting_currency_from'}
    
    popular_list = "\n".join([f"• {country} ({currency})" for country, currency in sorted(POPULAR_COUNTRIES.items())])
    
    bot.send_message(
        message.chat.id,
        "✈️ Создание нового путешествия\n\n"
        "Шаг 1/5: Выберите валюту отправления\n\n"
        "Вы можете:\n"
        "1️⃣ Написать название страны из списка ниже\n"
        "2️⃣ Написать код валюты напрямую (например: RUB, USD, EUR)\n\n"
        "📍 Популярные направления:\n" + popular_list + "\n\n"
        "💡 Поддерживаются все мировые валюты!"
    )


@bot.message_handler(commands=['balance'])
def balance_command(message):
    """Показать баланс активного путешествия"""
    user_id = message.from_user.id
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.send_message(message.chat.id, "У вас нет активного путешествия. Создайте новое с помощью /newtrip")
        return
    
    stats = db.get_trip_statistics(trip['trip_id'])
    
    text = (
        f"💰 Баланс путешествия: {trip['trip_name']}\n\n"
        f"📍 Маршрут: {trip['country_from']} → {trip['country_to']}\n"
        f"💱 Текущий курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}\n\n"
        f"💵 Текущий баланс:\n"
        f"  • {format_number(trip['balance_to'])} {trip['currency_to']}\n"
        f"  • {format_number(trip['balance_from'])} {trip['currency_from']}\n\n"
        f"📊 Статистика:\n"
        f"  • Начальная сумма: {format_number(trip['initial_amount_from'])} {trip['currency_from']}\n"
        f"  • Потрачено: {format_number(stats['total_spent_from'])} {trip['currency_from']}\n"
        f"  • Количество расходов: {stats['total_expenses']}"
    )
    
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['history'])
def history_command(message):
    """Показать историю расходов"""
    user_id = message.from_user.id
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.send_message(message.chat.id, "У вас нет активного путешествия.")
        return
    
    expenses = db.get_trip_expenses(trip['trip_id'], limit=15)
    
    if not expenses:
        text = f"📊 История расходов: {trip['trip_name']}\n\nПока нет записей о расходах."
    else:
        text = f"📊 История расходов: {trip['trip_name']}\n\n"
        for exp in expenses:
            date_str = exp['created_at'].split()[0] if ' ' in exp['created_at'] else exp['created_at']
            text += (
                f"📅 {date_str}\n"
                f"  💸 {format_number(exp['amount_to'])} {trip['currency_to']} "
                f"= {format_number(exp['amount_from'])} {trip['currency_from']}\n\n"
            )
    
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['switch'])
def switch_command(message):
    """Переключить активное путешествие"""
    user_id = message.from_user.id
    trips = db.get_all_trips(user_id)
    
    if not trips:
        bot.send_message(message.chat.id, "У вас пока нет путешествий.")
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for trip in trips:
        status = "✅" if trip['is_active'] else "⭕️"
        button_text = f"{status} {trip['trip_name']} ({trip['currency_from']} → {trip['currency_to']})"
        keyboard.add(
            types.InlineKeyboardButton(
                button_text,
                callback_data=f"switch_trip_{trip['trip_id']}"
            )
        )
    
    bot.send_message(
        message.chat.id,
        "🗂 Ваши путешествия:\n\nНажмите на путешествие, чтобы сделать его активным:",
        reply_markup=keyboard
    )


@bot.message_handler(commands=['setrate'])
def setrate_command(message):
    """Изменить курс обмена"""
    user_id = message.from_user.id
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.send_message(message.chat.id, "У вас нет активного путешествия.")
        return
    
    user_states[user_id] = {
        'state': 'waiting_new_rate',
        'trip_id': trip['trip_id']
    }
    
    text = (
        f"💱 Изменение курса для путешествия: {trip['trip_name']}\n\n"
        f"Текущий курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}\n\n"
        f"Введите новый курс обмена:"
    )
    
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обработчик всех текстовых сообщений"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Проверить, находится ли пользователь в процессе создания путешествия
    if user_id in user_states:
        state = user_states[user_id].get('state')
        
        if state == 'waiting_currency_from':
            handle_currency_from(message)
            return
        elif state == 'waiting_currency_to':
            handle_currency_to(message)
            return
        elif state == 'waiting_manual_rate':
            handle_manual_rate(message)
            return
        elif state == 'waiting_initial_amount':
            handle_initial_amount(message)
            return
        elif state == 'waiting_new_rate':
            handle_new_rate_input(message)
            return
    
    # Если сообщение — число, обработать как расход
    try:
        amount = float(text.replace(',', '.').replace(' ', ''))
        if amount > 0:
            handle_expense_amount(message, amount)
            return
    except ValueError:
        pass
    
    # Если ничего не подошло, показать справку
    bot.send_message(
        message.chat.id,
        "Я не понял команду. Используйте /menu для вызова главного меню или отправьте число для учёта расходов."
    )


def handle_currency_from(message):
    """Обработка ввода валюты/страны отправления"""
    user_id = message.from_user.id
    input_text = message.text.strip()
    
    # Определить валюту: либо по названию страны, либо по коду валюты
    currency = None
    country_name = None
    
    # Проверить, это название страны?
    if input_text in POPULAR_COUNTRIES:
        country_name = input_text
        currency = POPULAR_COUNTRIES[input_text]
    # Или это код валюты?
    elif input_text.upper() in [c.upper() for c in available_currencies.keys()]:
        currency = input_text.upper()
        # Найти название страны, если есть
        for country, curr in POPULAR_COUNTRIES.items():
            if curr == currency:
                country_name = country
                break
        if not country_name:
            country_name = get_currency_name(currency)
    # Попробовать найти частичное совпадение
    else:
        input_lower = input_text.lower()
        for country, curr in POPULAR_COUNTRIES.items():
            if input_lower in country.lower():
                country_name = country
                currency = curr
                break
    
    if not currency:
        bot.send_message(
            message.chat.id,
            f"❌ Валюта или страна '{input_text}' не найдена.\n\n"
            f"Попробуйте:\n"
            f"• Название страны: Россия, США, Китай\n"
            f"• Код валюты: RUB, USD, CNY, EUR, GBP\n\n"
            f"💡 Используйте /menu чтобы начать заново"
        )
        return
    
    user_states[user_id]['trip_creation'] = {
        'country_from': country_name or currency,
        'currency_from': currency
    }
    user_states[user_id]['state'] = 'waiting_currency_to'
    
    popular_list = "\n".join([f"• {c} ({curr})" for c, curr in sorted(POPULAR_COUNTRIES.items()) if curr != currency])
    
    bot.send_message(
        message.chat.id,
        f"✅ Валюта отправления: {currency} ({country_name or get_currency_name(currency)})\n\n"
        f"Шаг 2/5: Выберите валюту назначения\n\n"
        f"Напишите название страны или код валюты:\n\n"
        f"📍 Популярные направления:\n{popular_list}"
    )


def handle_currency_to(message):
    """Обработка ввода валюты/страны назначения"""
    user_id = message.from_user.id
    input_text = message.text.strip()
    
    # Определить валюту
    currency = None
    country_name = None
    
    # Проверить, это название страны?
    if input_text in POPULAR_COUNTRIES:
        country_name = input_text
        currency = POPULAR_COUNTRIES[input_text]
    # Или это код валюты?
    elif input_text.upper() in [c.upper() for c in available_currencies.keys()]:
        currency = input_text.upper()
        # Найти название страны, если есть
        for country, curr in POPULAR_COUNTRIES.items():
            if curr == currency:
                country_name = country
                break
        if not country_name:
            country_name = get_currency_name(currency)
    # Попробовать найти частичное совпадение
    else:
        input_lower = input_text.lower()
        for country, curr in POPULAR_COUNTRIES.items():
            if input_lower in country.lower():
                country_name = country
                currency = curr
                break
    
    if not currency:
        bot.send_message(
            message.chat.id,
            f"❌ Валюта или страна '{input_text}' не найдена.\n\n"
            f"Попробуйте:\n"
            f"• Название страны: Россия, США, Китай\n"
            f"• Код валюты: RUB, USD, CNY, EUR, GBP"
        )
        return
    
    trip_data = user_states[user_id]['trip_creation']
    
    if currency == trip_data['currency_from']:
        bot.send_message(
            message.chat.id,
            "❌ Валюта назначения не может совпадать с валютой отправления."
        )
        return
    
    trip_data['country_to'] = country_name or currency
    trip_data['currency_to'] = currency
    
    # Получить курс через API
    bot.send_message(message.chat.id, "⏳ Запрашиваю актуальный курс...")
    
    try:
        result = convert_currency(1, trip_data['currency_from'], trip_data['currency_to'])
        
        if result.get('success'):
            # API возвращает курс в info.quote, а результат конвертации в result
            rate = result.get('info', {}).get('quote')
            if not rate:
                # Fallback: используем result если это была конвертация 1 единицы
                rate = result.get('result')
            if rate:
                trip_data['api_rate'] = rate
                
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton("✅ Да", callback_data="confirm_rate_yes"),
                    types.InlineKeyboardButton("❌ Нет", callback_data="confirm_rate_no")
                )
                
                bot.send_message(
                    message.chat.id,
                    f"✅ Валюта назначения: {country_name or currency} ({currency})\n\n"
                    f"💱 Текущий курс обмена:\n"
                    f"1 {trip_data['currency_from']} = {rate:.4f} {currency}\n\n"
                    f"Шаг 3/5: Использовать этот курс?",
                    reply_markup=keyboard
                )
                return
        
        # Если API не вернул успешный результат
        error_msg = result.get('error', {}).get('info', 'Неизвестная ошибка')
        print(f"❌ API Error: {error_msg}")
        print(f"Full response: {result}")
        raise Exception(f"API Error: {error_msg}")
        
    except Exception as e:
        print(f"❌ Exception in currency conversion: {e}")
        bot.send_message(
            message.chat.id,
            f"⚠️ Не удалось получить курс от API.\n\n"
            f"Шаг 3/5: Пожалуйста, введите курс обмена вручную.\n"
            f"Формат: 1 {trip_data['currency_from']} = ? {trip_data['currency_to']}"
        )
        user_states[user_id]['state'] = 'waiting_manual_rate'


def handle_manual_rate(message):
    """Обработка ручного ввода курса"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        rate = float(text.replace(',', '.'))
        if rate <= 0:
            raise ValueError("Курс должен быть положительным числом")
        
        trip_data = user_states[user_id]['trip_creation']
        trip_data['exchange_rate'] = rate
        user_states[user_id]['state'] = 'waiting_initial_amount'
        
        bot.send_message(
            message.chat.id,
            f"✅ Курс принят: 1 {trip_data['currency_from']} = {rate:.4f} {trip_data['currency_to']}\n\n"
            f"Шаг 5/5: Введите начальную сумму в {trip_data['currency_from']}, "
            f"которую вы берёте с собой в путешествие:"
        )
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Неверный формат. Введите число (например, 12.5)"
        )


def handle_initial_amount(message):
    """Обработка ввода начальной суммы"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        amount = float(text.replace(',', '.').replace(' ', ''))
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        
        trip_data = user_states[user_id]['trip_creation']
        
        # Конвертировать через API для точности
        bot.send_message(message.chat.id, "⏳ Конвертирую начальную сумму...")
        
        try:
            result = convert_currency(amount, trip_data['currency_from'], trip_data['currency_to'])
            if result.get('success'):
                converted_amount = result.get('result', amount * trip_data['exchange_rate'])
            else:
                converted_amount = amount * trip_data['exchange_rate']
        except:
            converted_amount = amount * trip_data['exchange_rate']
        
        # Создать путешествие
        trip_name = f"{trip_data['country_from']} → {trip_data['country_to']}"
        trip_id = db.create_trip(
            user_id=user_id,
            trip_name=trip_name,
            country_from=trip_data['country_from'],
            country_to=trip_data['country_to'],
            currency_from=trip_data['currency_from'],
            currency_to=trip_data['currency_to'],
            exchange_rate=trip_data['exchange_rate'],
            initial_amount_from=amount,
            balance_to=converted_amount
        )
        
        # Очистить состояние
        del user_states[user_id]
        
        bot.send_message(
            message.chat.id,
            f"✅ Путешествие создано!\n\n"
            f"🎉 {trip_name}\n"
            f"💱 Курс: 1 {trip_data['currency_from']} = {trip_data['exchange_rate']:.4f} {trip_data['currency_to']}\n\n"
            f"💰 Стартовый баланс:\n"
            f"  • {format_number(converted_amount)} {trip_data['currency_to']}\n"
            f"  • {format_number(amount)} {trip_data['currency_from']}\n\n"
            f"Теперь вы можете отправлять мне числа, и я буду записывать их как расходы!",
            reply_markup=get_main_menu_keyboard()
        )
        
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Неверный формат. Введите число (например, 50000)"
        )


def handle_new_rate_input(message):
    """Обработка ввода нового курса обмена"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        new_rate = float(text.replace(',', '.'))
        if new_rate <= 0:
            raise ValueError("Курс должен быть положительным")
        
        trip_id = user_states[user_id]['trip_id']
        
        if db.update_exchange_rate(trip_id, new_rate):
            trip = db.get_active_trip(user_id)
            
            bot.send_message(
                message.chat.id,
                f"✅ Курс обмена обновлён!\n\n"
                f"💱 Новый курс: 1 {trip['currency_from']} = {new_rate:.4f} {trip['currency_to']}\n\n"
                f"💰 Пересчитанный баланс:\n"
                f"  • {format_number(trip['balance_to'])} {trip['currency_to']}\n"
                f"  • {format_number(trip['balance_from'])} {trip['currency_from']}"
            )
            
            # Очистить состояние
            del user_states[user_id]
        else:
            bot.send_message(message.chat.id, "❌ Ошибка при обновлении курса")
            
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Неверный формат. Введите число (например, 12.5)"
        )


def handle_expense_amount(message, amount):
    """Обработка суммы расхода"""
    user_id = message.from_user.id
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.send_message(
            message.chat.id,
            "У вас нет активного путешествия. Создайте его с помощью /newtrip"
        )
        return
    
    # Конвертировать сумму из валюты назначения в домашнюю валюту
    try:
        result = convert_currency(amount, trip['currency_to'], trip['currency_from'])
        if result.get('success'):
            converted_amount = result.get('result', amount / trip['exchange_rate'])
        else:
            converted_amount = amount / trip['exchange_rate']
    except:
        converted_amount = amount / trip['exchange_rate']
    
    # Сохранить данные о расходе для подтверждения
    if user_id not in user_states:
        user_states[user_id] = {}
    
    user_states[user_id]['pending_expense'] = {
        'amount_to': amount,
        'amount_from': converted_amount
    }
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Да", callback_data="confirm_expense_yes"),
        types.InlineKeyboardButton("❌ Нет", callback_data="confirm_expense_no")
    )
    
    bot.send_message(
        message.chat.id,
        f"💸 {format_number(amount)} {trip['currency_to']} = {format_number(converted_amount)} {trip['currency_from']}\n\n"
        f"Учесть как расход?",
        reply_markup=keyboard
    )


if __name__ == "__main__":
    print("🤖 Бот запускается...")
    print("📡 Загрузка списка валют из API...")
    if load_available_currencies():
        print(f"✅ Загружено {len(available_currencies)} валют")
    else:
        print("⚠️ Не удалось загрузить валюты из API, будут доступны только популярные")
    print("🚀 Бот запущен и готов к работе!")
    bot.infinity_polling()

