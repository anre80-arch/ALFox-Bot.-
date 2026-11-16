import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Настройка логирования (чтобы видеть ошибки в консоли)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Загружаем ключи из файла .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Настраиваем клиент DeepSeek (он совместим с OpenAI)
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# Здесь мы храним историю диалога (память агента)
user_memory = {}

# Системный промпт - здесь мы задаем характер и задачи агента
SYSTEM_PROMPT = """
Ты — мой личный ИИ-агент. Твоя задача — помогать мне с задачами, искать информацию и давать идеи.
Ты должен анализировать мои сообщения, запоминать мои предпочтения и привычки.
Отвечай кратко, структурированно и по делу. Если я прошу найти информацию, используй свои знания.
"""

# Функция для общения с ИИ
def ask_deepseek(user_id, user_text):
    # Если пользователь пишет впервые, создаем для него историю
    if user_id not in user_memory:
        user_memory[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Добавляем новое сообщение пользователя в память
    user_memory[user_id].append({"role": "user", "content": user_text})
    
    # Ограничиваем память последними 10 сообщениями, чтобы не перегружать модель
    if len(user_memory[user_id]) > 11:
        user_memory[user_id] = [user_memory[user_id][0]] + user_memory[user_id][-10:]

    try:
        response = client.chat.completions.create(
            model="deepseek-chat", # Используем актуальную модель
            messages=user_memory[user_id],
            stream=False
        )
        answer = response.choices[0].message.content
        # Сохраняем ответ агента в память
        user_memory[user_id].append({"role": "assistant", "content": answer})
        return answer
    except Exception as e:
        return f"Ошибка при обращении к ИИ: {e}"

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой личный агент. Напиши мне задачу, и я постараюсь её решить.")

# Обработчик команды /clear (очистка памяти)
async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_memory:
        del user_memory[user_id]
    await update.message.reply_text("Наша история диалога очищена. Начинаем с чистого листа.")

# Обработчик обычных сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text
    
    # Показываем, что бот "печатает"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Получаем ответ от ИИ
    answer = ask_deepseek(user_id, user_text)
    
    # Отправляем ответ в Telegram
    await update.message.reply_text(answer)

def main():
    # Создаём приложение бота
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_memory)) # Команда для очистки памяти
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    print("Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling()

if __name__ == '__main__':
    main()
