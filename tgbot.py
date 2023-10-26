import telebot
from telebot import types
import sqlite3
import atexit
import datetime
from config import token

bot = telebot.TeleBot(token)

def connect_db(chat_id):
    return sqlite3.connect(f'financial_data_{chat_id}.db')

def create_tables(chat_id):
    conn = connect_db(chat_id)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            comment TEXT,
            date DATE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            comment TEXT,
            date DATE
        )
    ''')

    conn.commit()
    conn.close()

def calculate_balance(chat_id):
    conn = connect_db(chat_id)
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(amount) FROM income')
    total_income = cursor.fetchone()[0] or 0
    cursor.execute('SELECT SUM(amount) FROM expenses')
    total_expenses = cursor.fetchone()[0] or 0
    conn.close()
    return total_income - total_expenses

@bot.message_handler(commands=["start"])
def start_message(message):
    chat_id = message.chat.id
    create_tables(chat_id)

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button1 = types.KeyboardButton(text="Record Income")
    button2 = types.KeyboardButton(text="Record Expense")
    button3 = types.KeyboardButton(text="View History")
    keyboard.add(button1, button2, button3)
    bot.send_message(chat_id, "Welcome!", reply_markup=keyboard)

def record_income(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Enter the income amount:")
    bot.register_next_step_handler(message, save_income)

def save_income(message):
    chat_id = message.chat.id
    try:
        amount = float(message.text)
        bot.send_message(chat_id, f"How did you earn {amount}? (e.g., salary, freelance)")
        bot.register_next_step_handler(message, lambda msg: save_income_with_comment(msg, amount))
    except ValueError:
        bot.send_message(chat_id, "Please enter a valid number.")
        start_message(message)

def save_income_with_comment(message, amount):
    chat_id = message.chat.id
    comment = message.text
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = connect_db(chat_id)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO income (amount, comment, date) VALUES (?, ?, ?)', (amount, comment, date))
    conn.commit()
    conn.close()
    bot.send_message(chat_id, f"Income of {amount} recorded with comment: {comment}.")
    start_message(message)

def record_expense(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Enter the expense amount:")
    bot.register_next_step_handler(message, save_expense)

def save_expense(message):
    chat_id = message.chat.id
    try:
        amount = float(message.text)
        bot.send_message(chat_id, f"What did you spend {amount} on? (e.g., groceries, rent)")
        bot.register_next_step_handler(message, lambda msg: save_expense_with_comment(msg, amount))
    except ValueError:
        bot.send_message(chat_id, "Please enter a valid number.")
        start_message(message)

def save_expense_with_comment(message, amount):
    chat_id = message.chat.id
    comment = message.text
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = connect_db(chat_id)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO expenses (amount, comment, date) VALUES (?, ?, ?)', (amount, comment, date))
    conn.commit()
    conn.close()
    bot.send_message(chat_id, f"Expense of {amount} recorded with comment: {comment}.")
    start_message(message)

def view_history(message):
    chat_id = message.chat.id
    conn = connect_db(chat_id)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM income')
    income_history = cursor.fetchall()

    cursor.execute('SELECT * FROM expenses')
    expense_history = cursor.fetchall()

    conn.close()

    income_message = "Income History:\n"
    for item in income_history:
        income_message += f"Date: {item[3]}, Amount: {item[1]}, Comment: {item[2]}\n"

    expense_message = "\nExpense History:\n"
    for item in expense_history:
        expense_message += f"Date: {item[3]}, Amount: {item[1]}, Comment: {item[2]}\n"

    total_balance = calculate_balance(chat_id)
    message_text = income_message + expense_message + f"\nTotal Balance: {total_balance}"
    bot.send_message(chat_id, message_text)
    start_message(message)

@bot.message_handler(content_types=["text"])
def repeat_all_messages(message):
    if message.text.lower() == "record income":
        record_income(message)
    elif message.text.lower() == "record expense":
        record_expense(message)
    elif message.text.lower() == "view history":
        view_history(message)

@atexit.register
def on_exit():
    for chat_id in active_users:
        connect_db(chat_id).close()

if __name__ == "__main__":
    bot.infinity_polling()
