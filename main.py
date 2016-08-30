import time

import telepot

import config
import log
import message


if __name__ == '__main__':
    bot = telepot.Bot(config.config['bot.token'])
    bot.message_loop(message.new_processor(bot))

    log.logging.info('Waiting for messages')
    while True:
        time.sleep(5)
