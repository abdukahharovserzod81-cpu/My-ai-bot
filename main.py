import os
import sys
import telebot
from telebot import apihelper
from flask import Flask
from threading import Thread
import logging
import time

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096

# ========== Импорт Google GenAI с fallback ==========
try:
    from google import genai
    GENAI_SDK = 'new'      # google-genai
except ImportError:
    try:
        import google.generativeai as genai
        GENAI_SDK = 'legacy'  # google-generativeai
    except ImportError:
        logger.error(
            "Не установлена ни google-genai, ни google-generativeai. "
            "Установите одну из них: pip install google-genai"
        )
        sys.exit(1)
# =====================================================

class Config:
    """Класс для конфигурации и проверки переменных окружения."""
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.port = int(os.environ.get("PORT", 10000))

    def validate(self):
        if not self.telegram_token:
            logger.error("Отсутствует TELEGRAM_TOKEN в переменных окружения!")
            return False
        if not self.gemini_api_key:
            logger.error("Отсутствует GEMINI_API_KEY в переменных окружения!")
            return False
        return True

class AIService:
    """Класс для работы с Gemini API."""
    def __init__(self, api_key: str):
        if GENAI_SDK == 'new':
            self.client = genai.Client(api_key=api_key)
            self.model_name = 'gemini-2.5-flash'
        else:  
            genai.configure(api_key=api_key)
            self.client = None  
            self.model_name = 'gemini-2.5-flash'  

    def generate_response(self, prompt: str) -> str:
        logger.info("Отправка запроса к модели Gemini...")
        if GENAI_SDK == 'new':
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            if response and response.text:
                return response.text
            return "Извините, модель не вернула текстовый ответ."
        else:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
            return "Извините, модель не вернула текстовый ответ."

class TelegramBotManager:
    """Класс для управления логикой Telegram бота."""
    def __init__(self, token: str, ai_service: AIService):
        self.bot = telebot.TeleBot(token)
        self.ai_service = ai_service
        self._register_handlers()

    def _register_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            welcome_text = (
                "Привет! Я твой продвинутый AI-бот на базе Google GenAI.\n"
                "Напиши мне любой вопрос, и я постараюсь помочь!"
            )
            self.bot.reply_to(message, welcome_text)

        @self.bot.message_handler(content_types=['text'])
        def handle_all_messages(message):
            user_id = message.from_user.id
            user_text = message.text

            if not user_text or not user_text.strip():
                self.bot.reply_to(message, "Пожалуйста, напишите текст запроса.")
                return

            logger.info(f"Получено сообщение от пользователя {user_id}: {user_text}")

            try:
                self.bot.send_chat_action(message.chat.id, 'typing')
                ai_answer = self.ai_service.generate_response(user_text)
                self._send_long_message(message.chat.id, ai_answer, reply_to=message.message_id)
            except Exception as e:
                logger.error(f"Ошибка при обработке запроса пользователя {user_id}: {e}")
                self.bot.reply_to(
                    message,
                    "Произошла ошибка при обработке запроса. Попробуйте ещё раз чуть позже."
                )

    def _send_long_message(self, chat_id, text: str, reply_to: int = None):
        """Разбивает длинные сообщения на части и отправляет их."""
        for i in range(0, len(text), TELEGRAM_MESSAGE_LIMIT):
            chunk = text[i:i + TELEGRAM_MESSAGE_LIMIT]
            if i == 0 and reply_to is not None:
                self.bot.send_message(chat_id, chunk, reply_to_message_id=reply_to)
            else:
                self.bot.send_message(chat_id, chunk)

    def start_polling(self):
        logger.info("Очистка старых вебхуков и подключений...")
        try:
            self.bot.remove_webhook()
        except Exception:
            pass

        logger.info("Запуск защищенного infinity_polling...")
        while True:
            try:
                # skip_pending=True предотвращает ответы на старые сообщения из-за крашей
                self.bot.infinity_polling(skip_pending=True, long_polling_timeout=60)
            except apihelper.ApiTelegramException as e:
                if e.error_code == 409:
                    logger.warning("Конфликт 409: Обнаружена другая копия бота. Ждем 15 секунд...")
                    time.sleep(15)
                else:
                    logger.error(f"Ошибка API Telegram: {e}")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Сбой в работе бота: {e}. Перезапуск через 5 секунд...")
                time.sleep(5)

class WebServer:
    """Класс для создания Flask-сервера-заглушки (нужен для Render)."""
    def __init__(self, port: int):
        self.app = Flask(__name__)
        self.port = port
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return "Telegram AI Bot is running and healthy!", 200

        @self.app.route('/health')
        def health_check():
            return {"status": "ok"}, 200

    def run(self):
        logger.info(f"Запуск веб-сервера Flask на порту {self.port}...")
        cli = sys.modules.get('flask.cli')
        if cli:
            cli.show_server_banner = lambda *args, **kwargs: None
        self.app.run(host="0.0.0.0", port=self.port, debug=False, use_reloader=False)

def main():
    logger.info("Инициализация запуска приложения...")

    config = Config()
    if not config.validate():
        sys.exit(1)

    ai_service = AIService(api_key=config.gemini_api_key)
    bot_manager = TelegramBotManager(token=config.telegram_token, ai_service=ai_service)
    web_server = WebServer(port=config.port)

    web_thread = Thread(target=web_server.run, daemon=True)
    web_thread.start()
    logger.info("Веб-сервер успешно запущен в фоновом потоке.")

    bot_manager.start_polling()

if __name__ == "__main__":
    main()
    
