import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from telegram import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup

import config
import telegramcalendar

import datetime
import dateutil.parser

import uuid
from threading import Timer

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


SET_DATE, SET_TIME, SET_TITLE, CONFIRM = range(4)


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    custom_keyboard = [['/list', '/set']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    text = ('Hi!'
        '\nThis is the reminder bot.'
        '\nIt can help you not to forget something important.')
    update.message.reply_text(text, reply_markup=reply_markup)


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def set_reminder_init(update, context):
    update.message.reply_text(text='set a date:\n\nuse "/cancel" command to cancel reminder.',
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
        text = (f'You selected {date_str_formatted}'
            '\nselect time'
            '\nformat: hh:mm'
            '\n\nuse "/cancel" command to cancel reminder.')
        context.bot.send_message(chat_id=update.callback_query.from_user.id,
                                text=text,
                                reply_markup=ReplyKeyboardRemove())
        return SET_TIME


def set_time(update, context):
    time_input = update.message.text

    # validate time input
    try:
        validtime = datetime.datetime.strptime(time_input, '%H:%M')
    except ValueError:
        logger.info('invalid time')
        update.message.reply_text('invalid time format.\nselect time\nformat: hh:mm')
        return SET_TIME

    date_time = str(context.user_data['date']) + ' ' + time_input
    date_time = dateutil.parser.parse(date_time)

    # check time has not passed
    if datetime.datetime.now() > date_time:
        logger.info('time has already passed')
        update.message.reply_text('time has already passed. set another time.')
        return SET_TIME

    context.user_data['date_time'] = date_time
    text = (f'time {time_input} has been set.'
        '\nset title:'
        '\n\nuse "/cancel" command to cancel reminder')
    update.message.reply_text(text)
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
    text = (f'reminder "{title}" has been set to: {date_time_str_formatted}'
        '\n\nset reminder?')
    update.message.reply_text(text,
                            reply_markup=reply_markup)
    return CONFIRM

def confirm(update, context):
    query = update.callback_query
    date_time = context.user_data['date_time']
    date_time_str = context.user_data['date_time_str']
    title = context.user_data['title']

    def send_reminder(*args):
        # delete expired reminder from user_data['reminders']
        context.user_data['reminders'] = [i for i in context.user_data['reminders'] if not (i['id'] == args[2])]
        logger.info(context.user_data)
        # send reminder message
        text = (f'it is a reminder: "{args[0]}"'
            f'\nthat had been set to: {args[1]}'
            '\n\nuse "/set" command to set new reminder.'
            '\nuse "/list" command to see your active reminders.')
        context.bot.send_message(chat_id=update.callback_query.from_user.id,
                                text=text)

    # if "ok" button was pressed
    if int(query.data):
        logger.info(context.user_data)
        # set timer and put it to context.user_data
        delay = (date_time - datetime.datetime.now()).total_seconds()
        if delay > 0:
            reminder_id = str(uuid.uuid1())
            if 'reminders' not in context.user_data:
                context.user_data['reminders'] = []
            ind = len(context.user_data['reminders'])
            obj = {
                'id': reminder_id,
                'title': title,
                'date_time': date_time,
                'date_time_str': date_time_str,
                'timer': Timer(delay, send_reminder, [title, date_time_str, reminder_id])
            }
            context.user_data['reminders'].append(obj)
            context.user_data['reminders'][ind]['timer'].start()
            # sort reminders list
            context.user_data['reminders'].sort(key=lambda item:item['date_time'])

            text = (f'reminder "{title}" has been set to: {date_time_str}'
                '\n\nuse "/set" command to set new reminder.'
                '\nuse "/list" command to see your active reminders.')
            query.edit_message_text(text)
        else:
            text_passed = ('time of your reminder has passed.'
                '\nset a new reminder please.'
                '\n\nuse "/set" command to set new reminder.'
                '\nuse "/list" command to see your active reminders.')
            query.edit_message_text(text_passed)
    # if "cancel" button was pressed
    else:
        logger.info(f'reminder {title} has been canceled')
        query.edit_message_text('reminder has been canceled.\nuse "/set" command to set new reminder.')

    # clear temp data
    del context.user_data['date'], context.user_data['date_time'], context.user_data['date_time_str'], context.user_data['title']
    logger.info(context.user_data)
    return ConversationHandler.END


def list_reminders(update, context):
    reminders = 'reminders' in context.user_data and context.user_data['reminders'] or []
    logger.info(reminders)
    if len(reminders) == 0:
        update.message.reply_text('there are no reminders set yet.\n\nuse "/set" command to set new reminder.')
        return
    s = 'your reminders:'
    for ind, item in enumerate(reminders):
        title = item['title']
        date_time_str = item['date_time_str']
        s += f'\n\n{ind + 1}) title: "{title}", time: {date_time_str}'
    text = s + ('\n\nuse "/set" command to set new reminder.'
        '\nuse "/delete" command with the number of reminder you want to delete.')
    update.message.reply_text(text)


def delete_reminder(update, context):
    if 'reminders' not in context.user_data or ('reminders' in context.user_data and len(context.user_data['reminders']) == 0):
        update.message.reply_text('there is nothing to delete.')
        return

    try:
        ind = int(update.message.text.split()[1].strip())
        ind = ind - 1
        if ind + 1 > len(context.user_data['reminders']):
            update.message.reply_text('can\'t find reminder with given number. please try again.')
    except ValueError:
        update.message.reply_text('can\'t find reminder with given number. please try again.')
        return

    title = context.user_data['reminders'][ind]['title']
    date_time_str = context.user_data['reminders'][ind]['date_time_str']
    context.user_data['reminders'][ind]['timer'].cancel()
    del context.user_data['reminders'][ind]
    text = (f'reminder "{title}" ({date_time_str}) has been deleted.'
        '\n\nuse "/set" command to set new reminder.'
        '\nuse "/list" command to see your active reminders.')
    update.message.reply_text(text)


def cancel(update, context):
    text = ('you have canceled a reminder.'
        '\n\nuse "/set" command to set new reminder.'
        '\nuse "/list" command to see your active reminders.')
    update.message.reply_text(text)
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
            CommandHandler('list', list_reminders),
            CommandHandler('delete', delete_reminder),
            # CommandHandler('cancel', cancel),
            # MessageHandler(Filters.text, echo)
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
