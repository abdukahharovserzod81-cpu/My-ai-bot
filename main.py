import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from tavily import TavilyClient

# Инициализация клиентов через переменные окружения
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой ИИ-ассистент с выходом в интернет. Задай мне любой вопрос!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_chat_action("typing")

    try:
        # 1. Поиск в интернете через Tavily
        search_res = tavily_client.search(query=user_text, search_depth="basic")
        context_data = "\n".join([f"- {r['content']}" for r in search_res.get("results", [])])

        # 2. Формирование ответа через Groq (Llama 3)
        prompt = f"Данные из интернета:\n{context_data}\n\nВопрос пользователя: {user_text}"
        
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ты умный помощник. Отвечай красиво, структурированно, с эмодзи и на языке пользователя, используя полученный контекст из интернета."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message.content
        await update.message.reply_text(answer, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text("Произошла ошибка при обработке запроса. Попробуйте позже.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
      
