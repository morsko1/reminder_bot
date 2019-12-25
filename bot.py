import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from telegram import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

import config
import telegramcalendar

import datetime
import dateutil.parser

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


SET_DATE, SET_TIME, SET_TITLE, CONFIRM = range(4)


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)

def set_reminder_init(update, context):
    update.message.reply_text(text='set a date:',
                            reply_markup=telegramcalendar.create_calendar())
    return SET_DATE

def set_date(update, context):
    selected,date = telegramcalendar.process_calendar_selection(context.bot, update)
    if selected:
        date_str = str(date).split()[0]
        # validate date input. check it has not passed
        today_str = str(str(datetime.datetime.now()).split()[0])
        today = datetime.datetime.strptime(today_str, "%Y-%m-%d").date()
        selected_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        if (selected_date < today):
            logger.info('date has already passed')
            context.bot.send_message(chat_id=update.callback_query.from_user.id,
                                text='date has already passed.\nset a date:',
                                reply_markup=telegramcalendar.create_calendar())
            return SET_DATE
        context.user_data['date'] = date_str
        date_str_formatted = datetime.datetime.strftime(selected_date, "%d.%m.%Y")
        logger.info(date_str_formatted)
        logger.info(type(date_str_formatted))
        context.bot.send_message(chat_id=update.callback_query.from_user.id,
                                text=f'You selected {date_str_formatted}\nselect a time\nformat: hh:mm',
                                reply_markup=ReplyKeyboardRemove())
        return SET_TIME

def set_time(update, context):
    time_input = update.message.text
    logger.info(time_input)

    # validate time input
    try:
        validtime = datetime.datetime.strptime(time_input, '%H:%M')
        logger.info('valid time')
    except ValueError:
        logger.info('invalid time (((')
        update.message.reply_text('invalid time format.\nselect a time\nformat: hh:mm')
        return SET_TIME

    date_time = str(context.user_data['date']) + ' ' + time_input
    date_time = dateutil.parser.parse(date_time)
    logger.info(date_time)

    # check time has not passed
    if datetime.datetime.now() > date_time:
        logger.info('time has already passed')
        update.message.reply_text('time has already passed. set a new time')
        return SET_TIME

    context.user_data['date_time'] = date_time
    update.message.reply_text(f'time {time_input} has been set.\nset title:')
    return SET_TITLE

def set_title(update, context):
    title = update.message.text
    context.user_data['title'] = title
    keyboard = [[InlineKeyboardButton('cancel', callback_data='0'),
                 InlineKeyboardButton('ok', callback_data='1')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    date_time = context.user_data['date_time']
    date_time_str_formatted = datetime.datetime.strftime(date_time, '%d.%m.%Y %H:%M')
    context.user_data['date_time_str'] = date_time_str_formatted
    update.message.reply_text(f'reminder has been set to: {date_time_str_formatted}\ntitle: "{title}"\n\nis that correct?',
                            reply_markup=reply_markup)
    return CONFIRM

def confirm(update, context):
    query = update.callback_query
    date_time_str = context.user_data['date_time_str']
    title = context.user_data['title']
    if int(query.data):
        logger.info(context.user_data)
        # set timer and put it to context.user_data
        query.edit_message_text(f'reminder has been set to: {date_time_str}\ntitle: "{title}"')
    else:
        logger.info(f'reminder {title} has been canceled')
        query.edit_message_text('reminder has been canceled')
    return ConversationHandler.END

def cancel(update, context):
    update.message.reply_text('Bye! I hope we can talk again some day.')
    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(config.token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
            CommandHandler('set', set_reminder_init),
            MessageHandler(Filters.text, echo)
        ],

        states={
            SET_DATE: [CallbackQueryHandler(set_date)],
            SET_TIME: [MessageHandler(Filters.text, set_time)],
            SET_TITLE: [MessageHandler(Filters.text, set_title)],
            CONFIRM: [CallbackQueryHandler(confirm)],
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
