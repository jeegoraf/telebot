from typing import Dict
import telebot
import sqlite3
from telebot import types

bot = telebot.TeleBot('5066457668:AAGrNLTfH_HUwkIeMn8rVEExUp79dZHO4xs')

conn = sqlite3.connect('userDatabase.db', check_same_thread=False)
cursor = conn.cursor()

cur_user = {}

# начало работы с ботом
# обработка команды /start - выбор роли (Организатор/Участник)


@bot.message_handler(commands='start')
def start(message, res=False):
    markup_inline = types.InlineKeyboardMarkup()
    item_org = types.InlineKeyboardButton(text='Организатор', callback_data='input_name_org')
    markup_inline.add(item_org)
    item_part = types.InlineKeyboardButton(text='Участник', callback_data='input_name_participant')
    markup_inline.add(item_part)
    bot.send_message(message.chat.id, 'Приветствую! Ты чьих будешь?', reply_markup=markup_inline)

# обработка данных с нажатий кнопок


@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    global cur_user

    # проверка на наличие пользователя в БД

    if call.data == 'input_name_org' or call.data == 'input_name_participant':
        bot.answer_callback_query(call.id)

        # cur_user - глобальная переменная для хранения данных пользователя
        cur_user["Role"] = 'Организатор' if call.data == 'input_name_org' else 'Участник'
        telegramID = call.message.from_user.id
        cur_user['TelegramID'] = telegramID

        # проверяем результаты запроса в БД по telegramID текущего пользователя

        sql = 'SELECT * FROM Users WHERE TelegramID=:telegramID'
        cursor.execute(sql, {'telegramID': telegramID})
        data = cursor.fetchone()

        # если запрос ничего не дал - даем пользователю ввести текст

        if data is None:
            bot.send_message(call.message.chat.id, 'Привет! Ты кто такой, а? Назовись!')
            return

        # если пользователь уже есть в БД - здороваемся и отправляем на подтверждение введенных данных

        else:
            bot.send_message(call.message.chat.id, 'Здравствуй, здравствуй, ' + str(data[2] + '!'))
            call.data = ['already_in_database', str(data[2])]

    # подтверждение введенных данных для пользователя ИЗ БД

    if call.data[0] == 'already_in_database':
        userName = call.data[1]
        cur_user['UserName'] = userName
        bot.send_message(call.message.chat.id, 'Ваше имя: ' + str(userName) + '\n' + 'Ваша роль: ' + str(cur_user['Role']))

        markup_inline = types.InlineKeyboardMarkup()
        item_org = types.InlineKeyboardButton(text='Да', callback_data='input_user_accepted')
        markup_inline.add(item_org)
        item_part = types.InlineKeyboardButton(text='Нет', callback_data='input_user_declined')
        markup_inline.add(item_part)
        bot.send_message(call.message.chat.id, 'Все верно?', reply_markup=markup_inline)

    # если данные введены верно - записываем пользователя в БД и отправляем в нужную ветку (участник/организатор)
    # в зависимости от данных

    if call.data == 'input_user_accepted':

        bot.answer_callback_query(call.id)

        try:

            db_add_user(cur_user['TelegramID'], cur_user['UserName'], cur_user['Role'])

        except:

            pass

        call.data = 'org' if cur_user['Role'] == 'Организатор' else 'participant'
        pass

    # если данные введены неверно - отправляем назад на выбор роли и т.д.

    if call.data == 'input_user_declined':
        cur_user = {}
        bot.answer_callback_query(call.id)
        markup_inline = types.InlineKeyboardMarkup()
        item_org = types.InlineKeyboardButton(text='Организатор', callback_data='input_name_org')
        markup_inline.add(item_org)
        item_part = types.InlineKeyboardButton(text='Участник', callback_data='input_name_participant')
        markup_inline.add(item_part)
        bot.send_message(call.message.chat.id, 'Что-то не так? Глаза разуй, блядь', reply_markup=markup_inline)

    # ветка "Организатор", выбор действия

    if call.data == 'org':
        bot.answer_callback_query(call.id)
        markup_inline = types.InlineKeyboardMarkup()
        item_create_event = types.InlineKeyboardButton(text='Создать мероприятие', callback_data='createEvent')
        markup_inline.add(item_create_event)
        item_events = types.InlineKeyboardButton(text='Список доступных мероприятий', callback_data='eventsList')
        markup_inline.add(item_events)
        # item_cancel_first = types.InlineKeyboardButton(text='Отмена', callback_data='cancelFirstChoice')
        # markup_inline.add(item_cancel_first)
        bot.send_message(call.message.chat.id, 'Что будем делать?', reply_markup=markup_inline)
        prev_message_id = call.message.message_id

    # ветка "Участник", список доступных для участника мероприятий

    if call.data == 'participant':
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, 'Я люблю Сашулика')

    elif call.data == 'cancelFirstChoice':
        bot.answer_callback_query(call.id)
        markup_inline = types.InlineKeyboardMarkup()
        item_org = types.InlineKeyboardButton(text='Организатор', callback_data='org')
        markup_inline.add(item_org)
        item_part = types.InlineKeyboardButton(text='Участник', callback_data='part')
        markup_inline.add(item_part)
        bot.send_message(call.message.chat.id, 'Так кто ж ты такой, а?', reply_markup=markup_inline)


# обработка введенного текста
# !!! НУЖНО СДЕЛАТЬ ВАЛИДАЦИЮ

@bot.message_handler(content_types='text')
def text_handler(message, table_name):
    global cur_user
    input_text = message.text
    text_arr = input_text.split(' ')

    if table_name == 'Users':
        cur_user['UserName'] = input_text
        bot.send_message(message.chat.id, 'Ваше имя: ' + str(input_text) + '\n' + 'Ваша роль: ' + str(cur_user['Role']))

        markup_inline = types.InlineKeyboardMarkup()
        item_org = types.InlineKeyboardButton(text='Да', callback_data='input_user_accepted')
        markup_inline.add(item_org)
        item_part = types.InlineKeyboardButton(text='Нет', callback_data='input_user_declined')
        markup_inline.add(item_part)
        bot.send_message(message.chat.id, 'Все верно?', reply_markup=markup_inline)


def db_add_user(TelegramID: int, FullName: str, Role: str):
    cursor.execute('INSERT INTO Users (TelegramID, FullName, Role) VALUES (?, ?, ?)',
                   (TelegramID, FullName, Role))
    conn.commit()


bot.infinity_polling()