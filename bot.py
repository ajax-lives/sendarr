#!/usr/bin/env python
import os, configparser, logging
from telegram import *
from sonarr import *
from radarr import *
from telegram.ext import *
from functools import wraps

class tgBot():
    def __init__(self):
        self.log = logging
        self.log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='tgbot_api.log',
                             filemode='w',
                             level=logging.INFO)
        self.config = configparser.ConfigParser()
        self.tgbot_token = ""
        self.tv = sonarrApi()
        self.movie = radarrApi()
        self.movie.load_config('dlconfig.cfg')
        self.tv.load_config('dlconfig.cfg')
        self.allowed_users = [ 309157084 ]
        self.type_search = 'movie'

    def load_config(self, configfile):
        """
        the config here should be in
        windows ini format at min it
        needs common and tgbot sections
        """
        try:
            self.config.read(configfile)
            self.tgbot_token = self.config['COMMON']['bot_token']
        except:
            self.log.error("Error reading config file {}".format(configfile))
            sys.exit(1)

    def restricted(func):
        @wraps(func)
        def wrapped(self, bot, update, *args, **kwargs):
            user_id = update.effective_user.id
            if user_id not in self.allowed_users:
                print("Unauthorized access denied for {}.".format(user_id))
                return
            return func(self, bot, update, *args, **kwargs)
        return wrapped

    def initBot(self):
        self.updater = Updater(token=self.tgbot_token)
        self.dispatcher = self.updater.dispatcher

    def searcher(self, terms):
        """
        blanket searcher takes self.type_search
        and searches either radarr or sonarr
        """
        self.search_param = ""
        self.resultlist = {}
        for x in terms:
            self.search_param += x + " "
        if self.type_search == 'movie':
            self.resultlist = self.movie.search_movie(self.search_param)
        else:
            self.resultlist = self.tv.search_series(self.search_param)
        return self.build_keyboard(self.resultlist)

    def build_keyboard(self, rlist):
        """
        this builds a keyboard telegram object
        from a list passed to args
        """
        self.keyboard = []
        for r in rlist:
            self.keyboard.append([InlineKeyboardButton(r, callback_data=rlist[r])])
        reply_markup = InlineKeyboardMarkup(self.keyboard)
        return reply_markup

    @restricted 
    def searchTV(self, bot, update, args):
        """
        this will search a sonarr server defined in sonarr.py
        it returns an inline keyboard to the user with the results
        """
        self.type_search = 'TV'
        reply_markup = self.searcher(args)
        update.message.reply_text('Found:', reply_markup=reply_markup)

    @restricted
    def download_button(self, bot, update):
        """
        this will be called once a user press's
        an inline keyboard button, it will call 
        in_library and add_series from sonarr.py
        or radarr.py and then it will inform the
        user of the status
        """
        query = update.callback_query
        self.Id = str(query.data)
        if self.type_search == 'movie':
            if self.movie.in_library(self.Id):
                bot.edit_message_text(text="sorry in library already",
                                      chat_id=query.message.chat_id,
                                      message_id=query.message.message_id)
            else:
                if self.movie.add_movie(self.Id):
                    bot.edit_message_text(text="Added, will be a few hours",
                                          chat_id=query.message.chat_id,
                                          message_id=query.message.message_id)
        else:
            if self.tv.in_library(self.Id):
                bot.edit_message_text(text="Sorry in library already", chat_id=query.message.chat_id,
                                      message_id=query.message.message_id)
            else:
                if self.tv.add_series(self.Id):
                    bot.edit_message_text(text="Added, should be available in about an hour", chat_id=query.message.chat_id,
                                          message_id=query.message.message_id)

    @restricted
    def searchMovies(self, bot, update, args):
        """
        this will search a radarr server defined in radarr.py
        it returns an inline keyboard to the user with the results
        """
        self.type_search = 'movie'
        reply_markup = self.searcher(args)
        update.message.reply_text('Found:', reply_markup=reply_markup)

    def startBot(self):
        self.updater.start_polling()

    def addHandlers(self):
        self.searchTV_handler = CommandHandler('TV', self.searchTV, pass_args=True)
        self.searchmovie_handler = CommandHandler('movie', self.searchMovies, pass_args=True)
        self.dispatcher.add_handler(self.searchTV_handler)
        self.dispatcher.add_handler(self.searchmovie_handler)
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.download_button))


if __name__ == "__main__":
    bot = tgBot()
    bot.load_config('dlconfig.cfg')
    bot.initBot()
    bot.addHandlers()
    bot.startBot()
