import os
import telebot
import google.generativeai as genai
from duckduckgo_search import DDGS

# Получаем ключи из настроек сервера
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверка ключей
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    print("Ошибка: Не найдены ключи TELEGRAM_TOKEN или GEMINI_API_KEY!")

# Настраиваем Gemini
genai.configure(api_key=GEMINI_API_KEY)
# Используем быструю и бесплатную модель
model = genai.GenerativeModel('gemini-1.5-flash')

# Запускаем бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я твой ИИ-бот с возможностью поиска в интернете. Задай мне любой вопрос!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text
    
    # Отправляем сообщение пользователю, что думаем
    sent_msg = bot.reply_to(message, "Ищу информацию в сети...")
    
    try:
        # Ищем свежие данные в DuckDuckGo
        search_results = ""
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(user_text, max_results=3)]
            search_results = "\n".join(results)
            
        # Формируем запрос для ИИ с учетом найденного в интернете
        prompt = f"""
        Пользователь спросил: {user_text}
        
        Вот свежая информация из интернета по этому вопросу:
        {search_results}
        
        Используй эту информацию и свои знания, чтобы дать точный, понятный и полезный ответ на языке пользователя.
        """
        
        response = model.generate_content(prompt)
        ai_answer = response.text
        
        bot.edit_message_text(ai_answer, chat_id=message.chat.id, message_id=sent_msg.message_id)
        
    except Exception as e:
        # Если поиск не сработал, отвечаем просто через ИИ
        try:
            response = model.generate_content(user_text)
            bot.edit_message_text(response.text, chat_id=message.chat.id, message_id=sent_msg.message_id)
        except Exception as err:
            bot.edit_message_text("Произошла ошибка при обработке запроса.", chat_id=message.chat.id, message_id=sent_msg.message_id)

# Бесконечный опрос серверов Telegram
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
