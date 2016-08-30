import time

import telepot

import config
import log
import message


if __name__ == '__main__':
    bot = telepot.Bot(config.config['bot.token'])
    bot.message_loop(message.new_processor(bot))

    log.logging.info('Waiting for messages')
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        bot.sendMessage(int(config.config['telegram.group.id']), message.bot_is_going_to_bed_message)
        quit()
