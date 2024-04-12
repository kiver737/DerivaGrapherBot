import telebot
from telebot import types
import numpy as np
import sympy as sp
import io
import matplotlib
from config import TOKEN, ADMIN_ID
from data import user_data, questions
import matplotlib.pyplot as plt
bot = telebot.TeleBot(TOKEN)
matplotlib.use('Agg')

def process_function(message):
    try:
        user_input = message.text
        x = sp.symbols('x')
        function = sp.sympify(user_input)
        derivative = sp.diff(function, x)
        critical_points = sp.solveset(derivative, x, domain=sp.S.Reals)
        response_message = f"Производная функции: {derivative}\nКритические точки: "

        # Форматирование критических точек с двумя знаками после запятой
        critical_points_list = [f"{point.evalf():.2f}" for point in critical_points if point.is_real]
        response_message += ', '.join(critical_points_list)

        # Отправка результатов
        bot.send_message(message.chat.id, response_message)

        # Создание графика
        fig, ax = plt.subplots()
        lam_f = sp.lambdify(x, function, modules=['numpy'])
        x_vals = np.linspace(-10, 10, 400)
        y_vals = lam_f(x_vals)
        ax.plot(x_vals, y_vals, label=f"{function}")

        # Отметка критических точек на графике
        for point in critical_points_list:
            y_val = lam_f(float(point))
            ax.plot(float(point), y_val, 'ro')

        ax.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        bot.send_photo(message.chat.id, photo=buf, caption="Ваш график:")
        plt.close(fig)

        # Отправка меню с выбором дальнейших действий
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Ввести новую функцию", callback_data="enter_function"))
        markup.add(types.InlineKeyboardButton("📗 Документация", callback_data="show_docs"))
        markup.add(types.InlineKeyboardButton("📙 Тестирование", callback_data="start_test"))
        bot.send_message(message.chat.id, "Выберите следующее действие:", reply_markup=markup)

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔍 Ввести функцию", callback_data="enter_function"))
    markup.add(types.InlineKeyboardButton("📚 Документация", callback_data="show_docs"))
    markup.add(types.InlineKeyboardButton("📝 Пройти тест", callback_data="start_test"))
    welcome_text = (
        "👋 Привет! Я 🤖 *Математический Бот* для анализа функций и проведения тестов.\n\n"
        "📈 Могу помочь найти *экстремумы* функций, показать их *графики* и проверить твои знания через тесты.\n\n"
        "Выбери одну из опций ниже для начала работы:"
    )
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=markup
    )


# Обработка ввода функции
@bot.callback_query_handler(func=lambda call: call.data == "enter_function")
def ask_for_function(call):
    msg = bot.send_message(call.message.chat.id,
                           "Введите вашу функцию в формате 'x**2 - 4*x + 4'. Используйте 'x' как переменную.")
    bot.register_next_step_handler(msg, process_function)


@bot.callback_query_handler(func=lambda call: call.data == "show_docs")
def show_docs(call):
    docs = (
        "📘 *Команды бота и их функции:*\n\n"
        "- 🚀 */start:* Запускает бота и показывает основное приветственное сообщение и меню. "
        "Используйте эту команду для начала работы с ботом.\n\n"
        "- ❓ */help:* Предоставляет подробную информацию о всех доступных командах и как ими пользоваться. "
        "Идеально подходит для новых пользователей, которым нужна помощь в навигации.\n\n"
        "- 📖 *Ввести функцию:* Позволяет пользователю ввести математическую функцию для анализа. "
        "Пример: отправьте 'x**2 - 4*x + 4' для получения производной, критических точек и графика функции.\n\n"
        "- 📖 *Тестирование:* Запускает серию вопросов для проверки ваших знаний по математике или другим дисциплинам. "
        "Пример: нажмите на кнопку 'Тестирование', чтобы начать серию вопросов с выбором ответов.\n\n"
        "- 📖 *Документация:* Предоставляет информацию о всех доступных командах бота и форматах ввода. "
        "Эта команда поможет вам ознакомиться с функциональностью бота и научиться им пользоваться.\n\n"
        "Используйте кнопки ниже для навигации по функциям или возврата в главное меню."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))
    bot.send_message(call.message.chat.id, docs, parse_mode='HTML', reply_markup=markup)



# Начало теста
@bot.callback_query_handler(func=lambda call: call.data == "start_test")
def start_test(call):
    user_data[call.from_user.id] = {"index": 0, "score": 0, "questions": questions}
    ask_question(call.message)


def ask_question(message):
    user_id = message.chat.id
    question_data = user_data[user_id]
    question_index = question_data['index']
    question = question_data['questions'][question_index]

    markup = types.InlineKeyboardMarkup(row_width=2)
    options_buttons = [
        types.InlineKeyboardButton(option, callback_data=f"answer_{idx}") for idx, option in
        enumerate(question['options'])
    ]
    markup.add(*options_buttons)

    # Добавим кнопку "Назад к предыдущему вопросу", если это не первый вопрос
    if question_index > 0:
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="prev_question"))

    markup.add(types.InlineKeyboardButton("⬅️ Вернуться в меню", callback_data="back_to_menu"))

    bot.send_message(
        user_id,
        f"Вопрос {question_index + 1}: {question['text']}",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    send_welcome(call.message)


# Обработка ответа и завершение теста
@bot.callback_query_handler(func=lambda call: call.data.startswith("answer_"))
def handle_answer(call):
    user_id = call.from_user.id
    question_data = user_data[user_id]
    question_index = question_data['index']
    question = question_data['questions'][question_index]
    selected_option = int(call.data.split('_')[1])

    # Сохраняем ответ в историю
    if 'answers' not in question_data:
        question_data['answers'] = {}
    question_data['answers'][question_index] = selected_option

    if selected_option == question['correct']:
        question_data['score'] += 1

    question_data['index'] += 1

    if question_data['index'] < len(question_data['questions']):
        ask_question(call.message)
    else:
        score = question_data['score']
        user_first_name = call.from_user.first_name  # Получаем имя пользователя
        user_last_name = call.from_user.last_name or ''  # Получаем фамилию пользователя, если есть
        user_full_name = f"{user_first_name} {user_last_name}".strip()
        final_message = f"Пользователь {user_full_name} (ID: {user_id}) завершил тест с результатом {score}/{len(question_data['questions'])}."
        bot.send_message(
            user_id,
            f"Тест завершен! Ваш счет: {score}/{len(question_data['questions'])}"
        )
        bot.send_message(
            ADMIN_ID,
            final_message
        )
        # Удаление данных пользователя из словаря после отправки сообщения администратору
        user_data.pop(user_id)


# Возврат к предыдущему вопросу
@bot.callback_query_handler(func=lambda call: call.data == "prev_question")
def go_back_to_prev_question(call):
    user_id = call.from_user.id
    question_data = user_data[user_id]
    if question_data['index'] > 0:
        question_data['index'] -= 1
        ask_question(call.message)
    else:
        bot.send_message(call.message.chat.id, "Это первый вопрос, назад вернуться нельзя.")
