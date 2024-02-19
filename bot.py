import asyncio
import mysql.connector
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, StateFilter
import logging

from aiogram.fsm.state import default_state

try:
    _token = open("cred.txt", "r").read()
    _dbCred = open("dbCred.txt", "r").read()
except FileExistsError:
    exit(404)

print(_dbCred) # DEBUG

mydb = mysql.connector.connect(
        host=_dbCred.split("host: ")[1].split("\n")[0],
        user=_dbCred.split("user: ")[1].split("\n")[0],
        password=_dbCred.split("password: ")[1].split("\n")[0],
        database=_dbCred.split("database: ")[1].split("\n")[0]
    )
mycursor = mydb.cursor()

dp = Dispatcher()

usersLocalDb = { } # Локальная база данных пользователей

async def InitNewUser(telegramUser : types.User, clean = False):
    if (not usersLocalDb.__contains__(telegramUser.id)) or (clean):
        usersLocalDb[telegramUser.id] = { }
        usersLocalDb[telegramUser.id]["getTaskNumber"] = False # Принимает ли бот на текущий момент число задания
        usersLocalDb[telegramUser.id]["getUserMenuItem"] = False # Принимает ли бот на текущий момент один из элементов из меню пользователя
        usersLocalDb[telegramUser.id]["getTaskAnswer"] = { }
        usersLocalDb[telegramUser.id]["getTaskAnswer"]["status"] = False # Принимает ли бот на текущий момент ответ на задание от пользователя
        usersLocalDb[telegramUser.id]["getTaskAnswer"]["id"] = None
        usersLocalDb[telegramUser.id]["getTaskAnswer"]["type"] = None
        usersLocalDb[telegramUser.id]["getTaskAnswer"]["answer"] = None
        usersLocalDb[telegramUser.id]["getTaskAnswer"]["answerNum"] = None
        usersLocalDb[telegramUser.id]["getTaskAnswer"]["imgSecondUrl"] = None
        usersLocalDb[telegramUser.id]["correctAnswer"] = False
        usersLocalDb[telegramUser.id]["inCorrectAnswer"] = False

    mycursor.execute(f"SELECT COUNT(`id`) FROM `users` WHERE `tgid` = {telegramUser.id};")
    myresult = mycursor.fetchall()

    if myresult[0][0] == 0:
        sql = "INSERT INTO `users` (`tgid`, `username`, `totalTasks`, `completeTasks`) VALUES (%s, %s, 0, 0);"
        val = (telegramUser.id, telegramUser.username)
        mycursor.execute(sql, val)
        mydb.commit()

async def main():
    _bot = Bot(token=_token)
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(_bot)

@dp.message(CommandStart())
async def start(message: types.Message):
    await InitNewUser(message.from_user, True)

    # Кнопки меню пользователя
    tasksListMenuButton = types.KeyboardButton(text="Начать решать!")
    userStatisticsMenuButton = types.KeyboardButton(text="Моя статистика")
    informationAboutBotMenuButton = types.KeyboardButton(text="О боте")

    userMenuMarkup = types.ReplyKeyboardMarkup(keyboard=[[tasksListMenuButton, userStatisticsMenuButton, informationAboutBotMenuButton]],
                                               resize_keyboard=True,
                                               input_field_placeholder="Выбери нужный пункт:")

    usersLocalDb[message.from_user.id]["getUserMenuItem"] = True
    await message.answer(text=f"Добро пожаловать, {message.from_user.first_name}! Наш бот является сборником заданий первой части для подготовки к ОГЭ по информатике. Бот не только выдаёт задания, но и автоматически проверяет ответ от пользователя, а также может показать правильный ответ и решение задания, если ответ пользователя оказался неверным. С помощью клавиатуры выбери задание, которое ты хочешь отработать:", reply_markup=userMenuMarkup)

@dp.message(Command("shutdown"), StateFilter(default_state))
async def ShutDownCommandHandler(message: types.Message):
    if (message.from_user.id == 703433131):
        mycursor.close()
        mydb.close()
        exit(0)

@dp.message()
async def MessageHandler(message: types.Message):
    await InitNewUser(message.from_user)

    # Если бот на текущий момент принимает номер задания
    if usersLocalDb[message.from_user.id]["getTaskNumber"]:
        match message.text:
            case "№ 1":
                mycursor.execute(f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                             reply_markup=types.ReplyKeyboardRemove()) # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove()) # изображение
                else:
                    if not file == None:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                             reply_markup=types.ReplyKeyboardRemove()) # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove()) # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 2":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 3":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 4":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 5":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 6":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 7":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 8":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 9":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 10":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 11":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case "№ 12":
                mycursor.execute(
                    f"SELECT `id`, `type`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {message.text.split("№ ")[1]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                taskType = myresult[0][1]
                text = myresult[0][2]
                imgUrl = myresult[0][3]
                answer = myresult[0][4]
                answerNum = myresult[0][5]
                file = myresult[0][6]
                imgSecondUrl = myresult[0][7]

                # Кнопки меню ответа
                tasksListMenuButton = types.KeyboardButton(text="Начать решать!")
                userStatisticsMenuButton = types.KeyboardButton(text="Моя статистика")
                informationAboutBotMenuButton = types.KeyboardButton(text="О боте")

                userMenuMarkup = types.ReplyKeyboardMarkup(
                    keyboard=[[tasksListMenuButton, userStatisticsMenuButton, informationAboutBotMenuButton]],
                    resize_keyboard=True,
                    input_field_placeholder="Выбери нужный пункт:")
                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст
                usersLocalDb[message.from_user.id]["getTaskNumber"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"] = taskType
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
            case _:
                await message.answer(f"{message.from_user.first_name}, вы выбрали неверный номер задания!")

    elif usersLocalDb[message.from_user.id]["getUserMenuItem"]:
        match message.text:
            case "Начать решать!":
                usersLocalDb[message.from_user.id]["getTaskNumber"] = True
                usersLocalDb[message.from_user.id]["getUserMenuItem"] = False

                # Кнопки с номерами заданий
                task1 = types.KeyboardButton(text="№ 1")
                task2 = types.KeyboardButton(text="№ 2")
                task3 = types.KeyboardButton(text="№ 3")
                task4 = types.KeyboardButton(text="№ 4")
                task5 = types.KeyboardButton(text="№ 5")
                task6 = types.KeyboardButton(text="№ 6")
                task7 = types.KeyboardButton(text="№ 7")
                task8 = types.KeyboardButton(text="№ 8")
                task9 = types.KeyboardButton(text="№ 9")
                task10 = types.KeyboardButton(text="№ 10")
                task11 = types.KeyboardButton(text="№ 11")
                task12 = types.KeyboardButton(text="№ 12")

                tasksMarkup = types.ReplyKeyboardMarkup(
                    keyboard=[[task1, task2, task3, task4, task5, task6],
                              [task7, task8, task9, task10, task11, task12]],
                    resize_keyboard=True,
                    input_field_placeholder="Выбери номер задания:")

                await message.answer(
                    text=f"{message.from_user.first_name}, с помощью клавиатуры выбери задание, которое хочешь отработать:",
                    reply_markup=tasksMarkup)

            case "Моя статистика":
                mycursor.execute(f"SELECT `totalTasks`, `completeTasks` FROM `users` WHERE `tgid` = {message.from_user.id};")
                myresult = mycursor.fetchall()
                await message.answer(f"Ваша статистика в боте: \n \n Всего решено заданий: {myresult[0][0]} \n Верно решённых заданий: {myresult[0][1]}")
            case "О боте":
                await message.answer("Наш бот является сборником заданий первой части для подготовки к ОГЭ по информатике. Бот не только выдаёт задания, но и автоматически проверяет ответ от пользователя, а также может показать правильный ответ и решение задания, если ответ пользователя оказался неверным \n Авторы: Николай Юрченко и Даниил Бойков")
            case _:
                await message.answer(f"{message.from_user.first_name}, вы выбрали несуществующий элемент в меню пользователя!")

    elif usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"]:
        # Кнопки меню ответа, если ответ пользователя неверный
        tryDoTaskAgainButton = types.KeyboardButton(text="Решить повторно")
        showAnswerButton = types.KeyboardButton(text="Показать ответ")
        # Кнопки меню ответа, если ответ пользователя верный
        getOtherTaskButton = types.KeyboardButton(text="Решить похожее задание")
        goToMenu = types.KeyboardButton(text="Вернуться в меню")

        answer = usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"]
        answerNum = usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"]

        correctAnswer = types.ReplyKeyboardMarkup(
            keyboard=[[getOtherTaskButton, goToMenu]],
            resize_keyboard=True,
            input_field_placeholder="Выбери нужный пункт:")

        inCorrectAnswer = types.ReplyKeyboardMarkup(
            keyboard=[[tryDoTaskAgainButton, showAnswerButton, goToMenu]],
            resize_keyboard=True,
            input_field_placeholder="Выбери нужный пункт:")

        sql = f"UPDATE `users` SET `totalTasks` = `totalTasks` + 1 WHERE `tgid` = {message.from_user.id};"
        mycursor.execute(sql)
        mydb.commit()

        if message.text == answerNum:
            sql = f"UPDATE `users` SET `completeTasks` = `completeTasks` + 1 WHERE `tgid` = {message.from_user.id};"
            mycursor.execute(sql)
            mydb.commit()
            await message.answer("Ты верно решил задание, поздравляю!",
                                 reply_markup=correctAnswer)
            usersLocalDb[message.from_user.id]["correctAnswer"] = True
        else:
            await message.answer("Ты неверно решил задание",
                                 reply_markup=inCorrectAnswer)
            usersLocalDb[message.from_user.id]["inCorrectAnswer"] = True

        usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = False

    elif usersLocalDb[message.from_user.id]["correctAnswer"] or usersLocalDb[message.from_user.id]["inCorrectAnswer"]:
        if message.text == "Вернуться в меню":
            # Кнопки меню пользователя
            tasksListMenuButton = types.KeyboardButton(text="Начать решать!")
            userStatisticsMenuButton = types.KeyboardButton(text="Моя статистика")
            informationAboutBotMenuButton = types.KeyboardButton(text="О боте")

            userMenuMarkup = types.ReplyKeyboardMarkup(
                keyboard=[[tasksListMenuButton, userStatisticsMenuButton, informationAboutBotMenuButton]],
                resize_keyboard=True,
                input_field_placeholder="Выбери нужный пункт:")

            await message.answer("Открыто меню пользователя бота",
                                 reply_markup=userMenuMarkup)
            usersLocalDb[message.from_user.id]["getUserMenuItem"] = True
            usersLocalDb[message.from_user.id]["correctAnswer"] = False
            usersLocalDb[message.from_user.id]["inCorrectAnswer"] = False
        if usersLocalDb[message.from_user.id]["correctAnswer"]:
            if message.text == "Решить похожее задание":
                mycursor.execute(
                    f"SELECT `id`, `text`, `img`, `answer`, `answerNum`, `file`, `img2` FROM `tasks` WHERE `type` = {usersLocalDb[message.from_user.id]["getTaskAnswer"]["type"]} ORDER BY rand() LIMIT 1")
                myresult = mycursor.fetchall()
                id = myresult[0][0]
                text = myresult[0][1]
                imgUrl = myresult[0][2]
                answer = myresult[0][3]
                answerNum = myresult[0][4]
                file = myresult[0][5]
                imgSecondUrl = myresult[0][6]

                if not imgUrl == None:
                    if not file == None:
                        await message.answer_photo(imgUrl,
                                                   f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение + файл
                    else:
                        await message.answer_photo(imgUrl, f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                                   reply_markup=types.ReplyKeyboardRemove())  # изображение
                else:
                    if not file == None:
                        await message.answer(
                            f"ID в базе данных: {id} \n \n Текст задания: \n \n {text} \n \n Ссылка на ресурс: {file}",
                            reply_markup=types.ReplyKeyboardRemove())  # файл
                    else:
                        await message.answer(f"ID в базе данных: {id} \n \n Текст задания: \n \n {text}",
                                             reply_markup=types.ReplyKeyboardRemove())  # текст

                usersLocalDb[message.from_user.id]["correctAnswer"] = False
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["id"] = id
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"] = answer
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"] = answerNum
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] = imgSecondUrl
        elif usersLocalDb[message.from_user.id]["inCorrectAnswer"]:
            if message.text == "Решить повторно":
                usersLocalDb[message.from_user.id]["getTaskAnswer"]["status"] = True
                usersLocalDb[message.from_user.id]["inCorrectAnswer"] = False
                await message.answer(f"{message.from_user.first_name}, введи новый ответ")
            elif message.text == "Показать ответ":
                if not usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"] == None:
                    await message.answer_photo(usersLocalDb[message.from_user.id]["getTaskAnswer"]["imgSecondUrl"],
                                               f"Ответ: {usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"]} \n \n Объяснение: \n {usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"]}")
                else:
                    await message.answer(f"Ответ: {usersLocalDb[message.from_user.id]["getTaskAnswer"]["answerNum"]} \n \n Объяснение: \n {usersLocalDb[message.from_user.id]["getTaskAnswer"]["answer"]}")
                # Кнопки меню пользователя
                tasksListMenuButton = types.KeyboardButton(text="Начать решать!")
                userStatisticsMenuButton = types.KeyboardButton(text="Моя статистика")
                informationAboutBotMenuButton = types.KeyboardButton(text="О боте")

                userMenuMarkup = types.ReplyKeyboardMarkup(
                    keyboard=[[tasksListMenuButton, userStatisticsMenuButton, informationAboutBotMenuButton]],
                    resize_keyboard=True,
                    input_field_placeholder="Выбери нужный пункт:")

                await message.answer("Открыто меню пользователя бота",
                                     reply_markup=userMenuMarkup)
                usersLocalDb[message.from_user.id]["getUserMenuItem"] = True
                usersLocalDb[message.from_user.id]["inCorrectAnswer"] = False
    else:
        # Кнопки меню пользователя
        tasksListMenuButton = types.KeyboardButton(text="Начать решать!")
        userStatisticsMenuButton = types.KeyboardButton(text="Моя статистика")
        informationAboutBotMenuButton = types.KeyboardButton(text="О боте")

        userMenuMarkup = types.ReplyKeyboardMarkup(
            keyboard=[[tasksListMenuButton, userStatisticsMenuButton, informationAboutBotMenuButton]],
            resize_keyboard=True,
            input_field_placeholder="Выбери нужный пункт:")

        await message.answer("Не понял твоего запроса",
                             reply_markup=userMenuMarkup)
        usersLocalDb[message.from_user.id]["getUserMenuItem"] = True

if __name__ == "__main__":
    asyncio.run(main())

mycursor.close()
mydb.close()