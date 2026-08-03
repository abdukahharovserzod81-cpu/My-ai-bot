import os
import telebot
from google import genai
from duckduckgo_search import DDGS

# Получаем ключи из настроек сервера
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверка ключей
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    print("Ошибка: Не найдены ключи TELEGRAM_TOKEN или GEMINI_API_KEY в переменных окружения!")
    exit(1)

# Настраиваем Gemini и Telegram
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я твой AI-бот. Напиши мне что-нибудь, и я отвечу.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text
    try:
        # Отправляем запрос к Gemini
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_text
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка при обращении к AI: {e}")

if __name__ == "__main__":
    print("Бот запущен и готов к работе...")
    bot.infinity_polling()
    
