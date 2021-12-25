from typing import Dict
import telebot
import sqlite3
from telebot import types

#bot = telebot.TeleBot('5066457668:AAGrNLTfH_HUwkIeMn8rVEExUp79dZHO4xs')
bot = telebot.TeleBot('5095240172:AAHkN0L2oOWa757GfsXD-LLXQ7PUAP7Seac')

conn = sqlite3.connect('userDatabase.db', check_same_thread=False)
cursor = conn.cursor()

cur_user = {}
cur_event = {}


# начало работы с ботом
# обработка команды /start - выбор роли (Организатор/Участник)

@bot.message_handler(commands='start')
def start(message, res=False):
    global cur_user
    cur_user['State'] = 'Start Screen'
    cur_user['TelegramID'] = message.from_user.id
    markup_inline = types.InlineKeyboardMarkup()
    item_org = types.InlineKeyboardButton(text='Организатор', callback_data='input_name_org')
    markup_inline.add(item_org)
    item_part = types.InlineKeyboardButton(text='Участник', callback_data='input_name_participant')
    markup_inline.add(item_part)
    bot.send_message(message.chat.id, 'Приветствую! Ты чьих будешь?', reply_markup=markup_inline)


# функции добавления записей в БД

def db_add_user(TelegramID: int, FullName: str, Role: str):
    cursor.execute('INSERT INTO Users (TelegramID, FullName, Role) VALUES (?, ?, ?)',
                   (TelegramID, FullName, Role))
    conn.commit()


def db_add_event(EventName: str, PeopleMaxCount: str, Date: str, Time: str, Place: str,
                 About: str, HashTags: str, ID_Org: int, Status: str):
    cursor.execute('INSERT INTO Events (EventName, PeopleMaxCount, Date, Time, Place, About, HashTags, ID_Org, Status) '
                   'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (EventName, PeopleMaxCount, Date, Time, Place, About, HashTags, ID_Org, Status))
    conn.commit()


def db_add_user_event(ID_USER: int, ID_EVENT: int):
    cursor.execute('INSERT INTO User_Event (ID_USER, ID_EVENT) VALUES (?, ?)',
                   (ID_USER, ID_EVENT))
    conn.commit()

# обработка данных с нажатий кнопок

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    global cur_user
    global cur_event

    # отмена мероприятия организатором 

    if 'cancel_event' in call.data:
        bot.answer_callback_query(call.id)
        i = len(call.data) - 1
        ID_Event = ''
        ID_User = call.from_user.id

        while call.data[i].isnumeric():
            ID_Event += call.data[i]
            i -= 1

        sql = """Update EVENTS set Status = ? where ID_EVENT=?"""
        cursor.execute(sql, ('CANCELLED', ID_Event))  

        sql = """SELECT EventName FROM EVENTS where ID_EVENT=?"""
        cursor.execute(sql, (ID_Event))
        event_name = cursor.fetchall()

        # sql = 'SELECT TelegramID from Users JOIN User_Event On ID_USER = TelegramID'
        # cursor.execute(sql)
        # data = cursor.fetchall()
        # for i in data:
        #     bot.send_message(i, f'Мероприятие {event_name} было отменено.')

        sql = """DELETE FROM User_Event where ID_Event=?"""
        cursor.execute(sql, (ID_Event))

        sql_update_event = """Update User_Event set PeopleCount = 0 where ID_EVENT=?"""
        cursor.execute(sql_update_event, ID_Event)


    if 'participants_list' in call.data:
        bot.answer_callback_query(call.id)
        i = len(call.data) - 1
        ID_Event = ''
        ID_User = call.from_user.id

        while call.data[i].isnumeric():
            ID_Event += call.data[i]
            i -= 1

        sql = 'SELECT FULLNAME from Users JOIN User_Event On ID_USER = TelegramID'
        cursor.execute(sql)
        data = cursor.fetchall()
        print(data)
        parts = ''

        for i in data:
            parts += str(i[0]) + '\n'

        bot.send_message(call.message.chat.id, parts)
        
    # обработка регистрации пользователя на мероприятие

    if 'register_to_Event' in call.data:
        bot.answer_callback_query(call.id)
        i = len(call.data) - 1
        ID_Event = ''

        while call.data[i].isnumeric():
            ID_Event += call.data[i]
            i -= 1

        ID_User = call.from_user.id

        sql = 'SELECT * FROM USER_EVENT WHERE ID_EVENT=? AND ID_User=?'
        cursor.execute(sql, (ID_Event, ID_User))
        data = cursor.fetchone()
        print(data)
        if data is None:
            db_add_user_event(ID_User, int(ID_Event))
            sql_update_event = """Update EVENTS set PeopleCount = PeopleCount + 1 where ID_EVENT=?"""
            cursor.execute(sql_update_event, ID_Event)
            conn.commit()

        call.data = 'participant'

    if 'cancel_registration_to_Event' in call.data:
        bot.answer_callback_query(call.id)
        i = len(call.data) - 1
        ID_Event = ''

        while call.data[i].isnumeric():
            ID_Event += call.data[i]
            i -= 1

        ID_User = call.from_user.id

        sql = 'DELETE FROM User_Event where ID_User=? AND ID_Event=?'
        cursor.execute(sql, (ID_User, ID_Event))
        data = cursor.fetchall()

        sql_update_event = """Update EVENTS set PeopleCount = PeopleCount - 1 where ID_EVENT=?"""
        cursor.execute(sql_update_event, ID_Event)
        conn.commit()
        call.data = 'participant'

    # внесение мероприятия в БД

    if call.data == 'input_event_accepted':
        bot.answer_callback_query(call.id)
        cur_event['ID_Org'] = cur_user['TelegramID']
        db_add_event(cur_event['EventName'], cur_event['PeopleMaxCount'], cur_event['Date'], cur_event['Time'], cur_event['Place']
                     , cur_event['About'], cur_event['HashTags'], cur_event['ID_Org'], 'Registration Opened')
        call.data = 'org'

    # проверка на наличие пользователя в БД

    if call.data == 'input_name_org' or call.data == 'input_name_participant':

        bot.answer_callback_query(call.id)

        # cur_user - глобальная переменная для хранения данных пользователя
        
        cur_user["Role"] = 'Организатор' if call.data == 'input_name_org' else 'Участник'
        telegramID = cur_user['TelegramID']

        # проверяем результаты запроса в БД по telegramID текущего пользователя

        sql = 'SELECT * FROM Users WHERE TelegramID=:telegramID'
        cursor.execute(sql, {'telegramID': telegramID})
        data = cursor.fetchone()

        # если запрос ничего не дал - даем пользователю ввести текст

        if data is None:
            cur_user['State'] = 'Input Name'
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

        cur_user['State'] = 'Add user to DB'

        bot.answer_callback_query(call.id)

        try:

            db_add_user(int(cur_user['TelegramID']), cur_user['UserName'], cur_user['Role'])

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
        bot.send_message(call.message.chat.id, 'Поаккуратнее на поворотах, братан!', reply_markup=markup_inline)

    # ветка "Организатор", выбор действия

    if call.data == 'org':
        bot.answer_callback_query(call.id)
        markup_inline = types.InlineKeyboardMarkup()
        item_create_event = types.InlineKeyboardButton(text='Создать мероприятие', callback_data='createEvent')
        markup_inline.add(item_create_event)
        item_events = types.InlineKeyboardButton(text='Мои мероприятия', callback_data='eventsList')
        markup_inline.add(item_events)
        bot.send_message(call.message.chat.id, 'Что будем делать?', reply_markup=markup_inline)

    # НАЧАЛО создания мероприятия
    # после выполнения этого if'a мы перемещаемся в функцию обработки текста (см.ниже, сразу за этой функцией)

    if call.data == 'createEvent':
        cur_event['PeopleCount'] = 0
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, 'Введите название мероприятия:')
        cur_user['State'] = 'Create Event Name'

    # ветка "Участник", список доступных для участника

    if call.data == 'participant':
        bot.answer_callback_query(call.id)
        markup_inline = types.InlineKeyboardMarkup()
        sql = 'SELECT * FROM Events WHERE Status!=?'
        cursor.execute(sql, ('CANCELLED',))
        data = cursor.fetchall()
        for i in range(len(data)):
            cancel_event = types.InlineKeyboardButton(text=data[i][1], callback_data='describe_Event' + str(data[i][0]))
            markup_inline.add(cancel_event)

        bot.send_message(call.message.chat.id, 'Список планируемых мероприятий:', reply_markup=markup_inline)

    # описание мероприятия по нажатию на кнопку из списка доступных мероприятий

    if 'describe_Event' in call.data:
        bot.answer_callback_query(call.id)
        i = len(call.data) - 1
        ID_Event = ''

        while call.data[i].isnumeric():
            ID_Event += call.data[i]
            i -= 1

        sql = 'SELECT * from Events WHERE ID_Event=:ID_Event'
        cursor.execute(sql, {'ID_Event': int(ID_Event)})
        data = cursor.fetchone()

        markup_inline = types.InlineKeyboardMarkup()

        # проверка регистрации пользователя на мероприятие
        # если он не зарегистрирован - рендерим кнопку "Зарегистрироваться"
        # если зарегистрирован - рендерим кнопку "Отменить регистрацию"

        sql_check_reg = 'SELECT * from User_Event Where ID_Event=? AND ID_User=?'
        cursor.execute(sql_check_reg, (int(ID_Event), call.from_user.id))
        data_check = cursor.fetchall()
        print(data_check)

        if data_check is None or len(data_check) == 0:
            cancel_event = types.InlineKeyboardButton(text='Зарегистрироваться', callback_data='register_to_Event'
                                                                                                    + str(data[0]))
            markup_inline.add(cancel_event)

        else:
            cancel_event = types.InlineKeyboardButton(text='Отменить регистрацию',
                                                           callback_data='cancel_registration_to_Event' + str(data[0]))
            markup_inline.add(cancel_event)

        bot.send_message(call.message.chat.id, 'Название мероприятия: ' + str(data[1]) + '\n'
                         + 'Максимальное количество участников: ' + str(data[2]) + '\n'
                         + 'Текущее количество участников:' + str(data[3]) + '\n'
                         + 'Дата: ' + str(data[4]) + '\n'
                         + 'Время: ' + str(data[5]) + '\n'
                         + 'Место проведения: ' + str(data[6]) + '\n'
                         + 'Описание: ' + str(data[7]), reply_markup=markup_inline)

    # список мероприятий, созданных текущим пользователем

    if call.data == 'eventsList':
        bot.answer_callback_query(call.id)
        markup_inline = types.InlineKeyboardMarkup()
        sql = 'SELECT * from Events where ID_Org=:ID_Org AND Status!=:Status'
        cursor.execute(sql, {'ID_Org': call.from_user.id, 'Status': 'CANCELLED'})
        data = cursor.fetchall()
        print(data)
        for i in range(len(data)):
            cancel_event = types.InlineKeyboardButton(text=data[i][1], callback_data='describe_event_org' + str(data[i][0]))
            markup_inline.add(cancel_event)

        bot.send_message(call.message.chat.id, 'Мои мероприятия:', reply_markup=markup_inline)

    if 'describe_event_org' in call.data:
        bot.answer_callback_query(call.id)
        i = len(call.data) - 1
        ID_Event = ''

        while call.data[i].isnumeric():
            ID_Event += call.data[i]
            i -= 1

        sql = 'SELECT * from Events WHERE ID_Event=:ID_Event'
        cursor.execute(sql, {'ID_Event': int(ID_Event)})
        data = cursor.fetchone()

        markup_inline = types.InlineKeyboardMarkup()

        parts_list = types.InlineKeyboardButton(text='Список участников', callback_data='participants_list'
                                                                                                + str(data[0]))
        markup_inline.add(parts_list)

        cancel_event = types.InlineKeyboardButton(text='Отменить мероприятие', callback_data='cancel_event'
                                                                                             + str(data[0]))
        markup_inline.add(cancel_event)

        bot.send_message(call.message.chat.id,  'Название мероприятия: ' + str(data[1]) + '\n'
                         + 'Максимальное количество участников: ' + str(data[2]) + '\n'
                         + 'Текущее количество участников:' + str(data[3]) + '\n'
                         + 'Дата: ' + str(data[4]) + '\n'
                         + 'Время: ' + str(data[5]) + '\n'
                         + 'Место проведения: ' + str(data[6]) + '\n'
                         + 'Описание: ' + str(data[7]), reply_markup=markup_inline)


# обработка введенного текста


@bot.message_handler(content_types='text')
def text_handler(message):
    global cur_user
    global cur_event
    input_text = message.text
    text_arr = input_text.split(' ')

    # обработка ввода имени пользователя

    if cur_user['State'] == 'Input Name':
        cur_user['UserName'] = input_text
        bot.send_message(message.chat.id, 'Ваше имя: ' + str(input_text) + '\n' + 'Ваша роль: ' + str(cur_user['Role']))

        markup_inline = types.InlineKeyboardMarkup()
        item_org = types.InlineKeyboardButton(text='Да', callback_data='input_user_accepted')
        markup_inline.add(item_org)
        item_part = types.InlineKeyboardButton(text='Нет', callback_data='input_user_declined')
        markup_inline.add(item_part)
        bot.send_message(message.chat.id, 'Все верно?', reply_markup=markup_inline)

    # обработка регистрации мероприятия

    if cur_user['State'] == 'Create Event Name':
        cur_event['EventName'] = input_text
        cur_user['State'] = 'Create Event PeopleMaxCount'
        bot.send_message(message.chat.id, 'Назовите максимальное количество участников:')

    elif cur_user['State'] == 'Create Event PeopleMaxCount':
        bot.send_message(message.chat.id, 'Введите дату проведения мероприятия:')
        cur_event['PeopleMaxCount'] = input_text
        cur_user['State'] = 'Create Event Date'

    elif cur_user['State'] == 'Create Event Date':
        bot.send_message(message.chat.id, 'Введите время проведения мероприятия:')

        cur_event['Date'] = input_text

        cur_user['State'] = 'Create Event Time'

    elif cur_user['State'] == 'Create Event Time':
        bot.send_message(message.chat.id, 'Введите место проведения мероприятия:')
        cur_event['Time'] = input_text
        cur_user['State'] = 'Create Event Place'

    elif cur_user['State'] == 'Create Event Place':
        bot.send_message(message.chat.id, 'Напишите краткое описание мероприятия:')
        cur_event['Place'] = input_text
        cur_user['State'] = 'Create Event About'

    elif cur_user['State'] == 'Create Event About':
        bot.send_message(message.chat.id, 'Добавьте хэштеги:')
        cur_event['About'] = input_text
        cur_user['State'] = 'Create Event HashTags'

    elif cur_user['State'] == 'Create Event HashTags':
        markup_inline = types.InlineKeyboardMarkup()
        item_org = types.InlineKeyboardButton(text='Все верно', callback_data='input_event_accepted')
        markup_inline.add(item_org)
        item_part = types.InlineKeyboardButton(text='Попробуем еще раз', callback_data='input_event_declined')
        markup_inline.add(item_part)
        bot.send_message(message.chat.id, 'Итак, проверим введенные данные:\n'
                         + 'Название мероприятия: ' + cur_event['EventName'] + '\n'
                         + 'Максимальное количество участников: ' + cur_event['PeopleMaxCount'] + '\n'
                         + 'Текущее количество участников: ' + str(cur_event['PeopleCount']) + '\n'
                         + 'Дата: ' + cur_event['Date'] + '\n'
                         + 'Время: ' + cur_event['Time'] + '\n'
                         + 'Место проведения: ' + cur_event['Place'] + '\n'
                         + 'Описание: ' + cur_event['About'], reply_markup=markup_inline)
        cur_event['HashTags'] = input_text


bot.infinity_polling()
