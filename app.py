#!/usr/bin/env python3
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from random import shuffle
import requests
from reply import Reply, Judge


def Reply_markup(have_hint):
    keyboard = [[InlineKeyboardButton('A', callback_data='0'),
                 InlineKeyboardButton('B', callback_data='1'),
                 InlineKeyboardButton('C', callback_data='2'),
                 InlineKeyboardButton('D', callback_data='3')]]
    if have_hint:
        keyboard.append([InlineKeyboardButton('Hint', callback_data='hint')])

    return InlineKeyboardMarkup(keyboard)


def Randomize_option(uid):
    global option_mapping
    option_mapping[uid] = [0, 1, 2, 3]
    shuffle(option_mapping[uid])


def Generate_problem(uid):
    global entity
    entity[uid] = requests.get(url+'/question?user='+uid).json()
    Randomize_option(uid)
    op = entity[uid]['option']
    om = option_mapping[uid]
    for i in range(len(op)):
        entity[uid]['question'] += '\n(' + chr(ord('A')+i) + ') ' + op[om[i]]

    return entity[uid]['question']


def Finish(uid):
    stat = requests.get(url+'/user?user='+uid).json()
    total = len(stat['questionStatus'])

    if stat['questionStatus'].count(2) == total:
        return Reply('allpass')
    elif stat['questionStatus'].count(1) == total:
        return Reply('allwrong')

    return Reply('finish')


def Start(bot, update):
    global entity, last_msg
    chat_id = update.message.chat_id
    uid = str(chat_id)

    if uid in last_msg:
        print('Clear board')
        bot.edit_message_text(chat_id=chat_id, message_id=last_msg[uid].message_id, text=entity[uid]['question'])

    requests.post(url+'/user', json={'user': uid, 'nickname': update.message.from_user.first_name, 'platform': 'telegram'})
    bot.send_message(chat_id=chat_id, text=Reply('welcome'))
    last_msg[uid] = bot.send_message(chat_id=chat_id, text=Generate_problem(uid),
                     reply_markup=Reply_markup(have_hint=(entity[uid]['hint'] != '')))


def Receive_and_reply(bot, update):
    rcv = update.callback_query
    chat_id = rcv.message.chat_id
    uid = str(chat_id)
    message_id = rcv.message.message_id

    if rcv.data == 'hint':
        reply = entity[uid]['question'] + '\nHint:\n' + entity[uid]['hint']

        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=reply,
                              reply_markup=Reply_markup(have_hint=False))
    else:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=entity[uid]['question'])

        id = entity[uid]['id']
        op = entity[uid]['option']
        om = option_mapping[uid]

        result = requests.post(url+'/answer', json={'user': uid, 'id': id, 'answer': om[int(rcv.data)]}).json()
        bot.send_message(chat_id=chat_id, text=op[om[int(rcv.data)]])
        bot.send_message(chat_id=chat_id, text=Judge(result))
        if id == 'finish':
            bot.send_message(chat_id=chat_id, text=Finish(uid))

        last_msg[uid] = bot.send_message(chat_id=chat_id, text=Generate_problem(uid),
                         reply_markup=Reply_markup(have_hint=(entity[uid]['hint'] != '')))


def Status(bot, update):
    chat_id = update.message.chat_id
    uid = str(chat_id)
    stat = requests.get(url+'/user?user='+uid).json()
    remainders = stat['questionStatus'].count(0)
    reply = 'Score: ' + str(stat['point']) + '\nRank: ' + str(stat['order'])
    if remainders > 0:
        reply += '\nRemainders: ' + str(remainders)
    else:
        reply += '\nGame Completed!'

    bot.send_message(chat_id=chat_id, text=reply)


def Statistic(bot, update):
    reply = 'http://leaderboard.ccns.ncku.edu.tw'
    bot.send_message(chat_id=update.message.chat_id, text=reply)


def Feedback(bot, update):
    reply = 'Submit a new issue:\nhttps://github.com/ccns/quiz-chatbot-tg/issues\nor contact us:\nhttps://www.facebook.com/ncku.ccns'
    bot.send_message(chat_id=update.message.chat_id, text=reply)


def main():
    global entity, option_mapping, url, last_msg

    entity = {}
    last_msg = {}
    option_mapping = {}

    url = '<url>'
    updater = Updater(token='<token>')
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CallbackQueryHandler(Receive_and_reply))
    dispatcher.add_handler(CommandHandler('start', Start))
    dispatcher.add_handler(CommandHandler('status', Status))
    dispatcher.add_handler(CommandHandler('statistic', Statistic))
    dispatcher.add_handler(CommandHandler('feedback', Feedback))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
