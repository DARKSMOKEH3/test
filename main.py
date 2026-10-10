from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8827544517:AAGWx24zKPOxscSOMueY4C8MQZJKhLc49Rk"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("ربات روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
