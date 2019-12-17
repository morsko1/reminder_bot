import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from telegram import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

import config
import telegramcalendar

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# SET_DATE = 'SET_DATE'
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
        context.bot.send_message(chat_id=update.callback_query.from_user.id,
                                text='You selected ' + str(date).split()[0] + '\nselect a time:\nformat: hh:mm',
                                reply_markup=ReplyKeyboardRemove())
        return SET_TIME

def set_time(update, context):
    update.message.reply_text('time ' + update.message.text + ' has been set. set title')
    return SET_TITLE

def set_title(update, context):
    update.message.reply_text('title ' + update.message.text + ' set')
    keyboard = [[InlineKeyboardButton("cancel", callback_data='0'),
                 InlineKeyboardButton("ok", callback_data='1')]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('is that correct?', reply_markup=reply_markup)
    return CONFIRM

def confirm(update, context):
    query = update.callback_query

    query.edit_message_text(int(query.data) and 'reminder has been set' or 'canceled')
    return ConversationHandler.END

def cancel(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
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
