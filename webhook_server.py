import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler, WebhookHandler
import requests
import aiohttp
from aiohttp import web
import os

# Включите логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ваш токен API для бота @BarsNskBot
TOKEN = os.getenv('TOKEN')

# URL вашего сервера для вебхука
RENDER_APP_NAME = os.getenv('RENDER_APP_NAME', 'bars-nsk-bot')
WEBHOOK_URL = f'https://{RENDER_APP_NAME}.onrender.com/webhook'

# Порт для сервера
PORT = int(os.getenv('PORT', 8000))

# Этапы диалога для записи на услугу
NAME, PHONE, DATE_TIME = range(3)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text('Привет! Я бот автосервиса БАРС. Чем могу помочь?')
    else:
        logger.warning('No message in update: %s', update)

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text('Доступные команды:\n/start - Начать\n/help - Помощь\n/info - Информация о нас\n/services - Услуги\n/services_buttons - Услуги (кнопки)\n/book - Записаться на услугу')
    else:
        logger.warning('No message in update: %s', update)

# Команда /info
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        info_text = (
            "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ \"БАРС\"\n"
            "Юридический адрес: 630005, Новосибирск, улица Журинская, д. 78\n"
            "Фактический адрес: 630005, Новосибирск, улица Фрунзе, 104А\n"
            "Телефон: +7(383)367-11-00\n"
            "WhatsApp: +79293871100\n"
            "Сайт: https://servis-bars.ru \n"
            "Instagram: https://www.instagram.com/servisbars_ru/ \n"
            "E-mail: zicn@yandex.ru"
        )
        await update.message.reply_text(info_text)
    else:
        logger.warning('No message in update: %s', update)

# Команда /services
async def services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        services_text = (
            "Услуги автосервиса БАРС:\n"
            "- Заправка\n"
            "- Диагностика\n"
            "- Ремонт двигателя\n"
            "- Ремонт ходовой части\n"
            "- Замена масла и фильтров\n"
            "- Техническое обслуживание\n"
            "- Шиномонтаж\n"
            "Подробнее на сайте: https://servis-bars.ru/uslugi "
        )
        await update.message.reply_text(services_text)
    else:
        logger.warning('No message in update: %s', update)

# Команда /services_buttons
async def services_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        keyboard = [
            [InlineKeyboardButton("Заправка", callback_data='fill_up')],
            [InlineKeyboardButton("Диагностика", callback_data='diagnostics')],
            [InlineKeyboardButton("Ремонт двигателя", callback_data='engine_repair')],
            [InlineKeyboardButton("Ремонт ходовой части", callback_data='chassis_repair')],
            [InlineKeyboardButton("Замена масла и фильтров", callback_data='oil_change')],
            [InlineKeyboardButton("Техническое обслуживание", callback_data='maintenance')],
            [InlineKeyboardButton("Шиномонтаж", callback_data='tyre_service')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выберите услугу:', reply_markup=reply_markup)
    else:
        logger.warning('No message in update: %s', update)

# Обработчик кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text=f"Вы выбрали услугу: {query.data}")
    else:
        logger.warning('No callback_query in update: %s', update)

# Команда /book
async def book_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Введите ваше имя:")
        return NAME
    else:
        logger.warning('No message in update: %s', update)
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        name = update.message.text
        context.user_data['name'] = name
        await update.message.reply_text("Введите ваш номер телефона:")
        return PHONE
    else:
        logger.warning('No message in update: %s', update)
        return ConversationHandler.END

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        phone = update.message.text
        context.user_data['phone'] = phone
        await update.message.reply_text("Введите желаемую дату и время:")
        return DATE_TIME
    else:
        logger.warning('No message in update: %s', update)
        return ConversationHandler.END

async def get_date_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        date_time = update.message.text
        context.user_data['date_time'] = date_time

        name = context.user_data.get('name', '')
        phone = context.user_data.get('phone', '')
        date_time = context.user_data.get('date_time', '')

        if send_to_crm(name, phone, date_time):
            booking_text = (
                f"Ваша запись на услугу:\n"
                f"Имя: {name}\n"
                f"Телефон: {phone}\n"
                f"Дата и время: {date_time}\n"
                f"Благодарим за запись!"
            )
            await update.message.reply_text(booking_text)
            # Отправка сообщения от имени @STOBARS
            await send_message_from_official_account(name, phone, date_time)
        else:
            await update.message.reply_text("Произошла ошибка при записи. Пожалуйста, попробуйте снова.")

        return ConversationHandler.END
    else:
        logger.warning('No message in update: %s', update)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Процесс записи отменен.")
        return ConversationHandler.END
    else:
        logger.warning('No message in update: %s', update)
        return ConversationHandler.END

def send_to_crm(name, phone, date_time):
    url = "https://your-crm-system.com/api/bookings "
    data = {
        "name": name,
        "phone": phone,
        "date_time": date_time
    }
    response = requests.post(url, json=data)
    return response.status_code == 200

# Отправка сообщения от имени @STOBARS
async def send_message_from_official_account(name, phone, date_time):
    official_token = os.getenv('OFFICIAL_TOKEN')
    url = f"https://api.telegram.org/bot {official_token}/sendMessage"
    chat_id = os.getenv('CHAT_ID')
    message_text = (
        f"Новая запись на услугу:\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Дата и время: {date_time}"
    )
    data = {
        "chat_id": chat_id,
        "text": message_text
    }
    response = requests.post(url, data=data)
    if response.status_code != 200:
        logger.error('Failed to send message from official account: %s', response.text)

# Обработчик текстовых сообщений
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(f'Вы написали: {update.message.text}')
    else:
        logger.warning('No message in update: %s', update)

# Обработчик ошибок
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)

async def handle_webhook(request):
    try:
        update = Update.de_json(await request.json(), application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
    return web.Response()

app = web.Application()
app.router.add_post('/webhook', handle_webhook)

def main() -> None:
    global application
    # Создайте приложение
    application = ApplicationBuilder().token(TOKEN).webhook_url(WEBHOOK_URL).build()

    # Регистрируйте обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("services", services))
    application.add_handler(CommandHandler("services_buttons", services_buttons))
    application.add_handler(CommandHandler("book", book_service))

    # Регистрируйте обработчик конечного автомата
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('book', book_service)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            DATE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date_time)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)

    # Регистрируйте обработчик кнопок
    application.add_handler(CallbackQueryHandler(button))

    # Регистрируйте обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Регистрируйте обработчик ошибок
    application.add_error_handler(error)

if __name__ == '__main__':
    main()