import json
import re

import config
import database
import finance
import log

# You need to register those commands for your bot to work using the Botfather.
commands = {
    'add credit': '/add',
    'undo': '/undo',
    'stats': '/stats',
    'bill': '/bill',
    'help': '/help',
}

help_text = 'Hi %s!\nYou can send me credits via the "/add" command. ' + \
            'The format is /add <debtor> <amount> <description>.'
unknown_request_text = "Sorry %s, I didn't understand your request. Try /help for more infos."
credit_success_text = 'Alright %s! I noted down that you have lent %.2f Euros to %s for %s.'
greeting_text = 'Hi %s!\nTry /help for more infos.'
no_user_mentioned_text = "%s, you didn't mention a user whom you credited. Use @<user> to mention a user."
invalid_credit_format_text = '%s, the format you used is incorrect. ' + \
                             'Please use the following format: /add <debtor> <amount> <description>.'
do_not_credit_the_bot = "Sorry %s,\nyou cannot lend me money. I don't need any :)"
undo_info = 'If you want to undo this credit just tell me "/undo %d".'
invalid_undo_request_format_text = '%s, the format you used is incorrect. ' + \
                                   'Please use the following format: /undo <credit id>.'
undo_success_text = 'Alright %s! I crossed out the line indicating that you have lent %.2f Euros to %s.'
invalid_stats_request_format_text = '%s, the format you used is incorrect. ' + \
                                    'Please use the following format: /stats <user>'
no_credits_for_user = "I don't have any credits that involve %s."

bot_is_going_to_bed_message = "Good night folks! I'm going to bed, see you tomorrow!"


def is_credit(msg):
    """Evaluate if this message adds a credit.

    :param msg: dict, Telegram message
    :return: bool, True if message is prefixed with the appropriate command
    """
    if 'text' not in msg:
        return False
    return msg['text'].startswith(commands['add credit'])


def is_undo(msg):
    """Evaluate if this message undoes a credit.

    :param msg: dict, Telegram message
    :return: bool, True if message is prefixed with the appropriate command
    """
    if 'text' not in msg:
        return False
    return msg['text'].startswith(commands['undo'])


def is_stats(msg):
    """Evaluate if this message requests the credit stats.

    :param msg: dict, Telegram message
    :return: bool, True if message is prefixed with the appropriate command
    """
    if 'text' not in msg:
        return False
    return msg['text'].startswith(commands['stats'])


def is_bill_request(msg):
    """Evaluate if this message requests the bill.

    :param msg: dict, Telegram message
    :return: bool, True if message is prefixed with the appropriate command
    """
    if 'text' not in msg:
        return False
    return msg['text'].startswith(commands['bill'])


def is_help_request(msg):
    """Evaluate if this message is a request for more information about the bots usage.

    :param msg: dict, Telegram message
    :return: bool, True if message is prefixed with the appropriate command
    """
    if 'text' not in msg:
        return False
    return msg['text'].startswith(commands['help'])


def is_new_user(msg):
    """Evaluate if this message indicates a new user that joined the group.

    :param msg: dict, Telegram message
    :return: bool, True if this message indicates a new user
    """
    return 'new_chat_member' in msg


def is_user_left(msg):
    """Evaluate if this message indicates a user that left the group.

    :param msg: dict, Telegram message
    :return: bool, True if this message indicates a user that left the group
    """
    return 'left_chat_member' in msg


def extract_credit(msg):
    """Build a credit object from a Telegram message.
    Credit objects are represented by dicts and contain the following keys:
        * id: Unique identifier of the credit; this is the message_id the credit came from (integer)
        * donor: The user who issued the credit (Telegram User object)
        * debtor: The user who received the credit (Telegram User object)
        * amount: The amount of money that was lent (float)
        * description: A description of this credit (string)

    Raises a RuntimeError if the message contains invalid information.

    :param msg: dict, Telegram message
    :return: dict, credit object
    """
    credit = {'donor': msg['from'], 'id': msg['message_id']}
    try:
        # Users can be mentioned via either 'text_mention' or 'mention'.
        mention = next(
            entity for entity in msg['entities'] if entity['type'] == 'text_mention' or entity['type'] == 'mention')
    except (StopIteration, KeyError):
        log.logging.warning('No user mentioned: %s' % msg)
        raise RuntimeError(no_user_mentioned_text % msg['from']['first_name'])

    if mention['type'] == 'text_mention':
        # The entity contains a user dict containing name and if of the user.
        credit['debtor'] = mention['user']

    # We allow Umlaute in a word or name
    word_chars = 'A-Za-z\s\xe4\xc4\xf6\xd6\xfc\xdc\xdf'
    pattern = r'^%s (?P<debtor>[@%s]+)(?P<amount>[.0-9]+) (?P<description>[%s]+)$' % (commands['add credit'],
                                                                                      word_chars, word_chars)
    match = re.match(pattern, msg['text'])
    if match is None:
        log.logging.warning('Invalid credit format: %s' % msg)
        raise RuntimeError(invalid_credit_format_text % msg['from']['first_name'])
    log.logging.debug('groupdict(): %s' % match.groupdict())

    credit['amount'] = eval(match.groupdict()['amount'])
    credit['description'] = match.groupdict()['description'].strip()

    debtor = match.groupdict()['debtor'].strip()

    if mention['type'] == 'mention':
        # The entity does not contain a user dict but the user id is present in the message text.
        # The user id starts with a '@' in this case.
        if debtor.startswith('@'):
            if debtor[1:] == config.config['bot.name']:
                log.logging.warning('Do not credit the bot')
                raise RuntimeError(do_not_credit_the_bot % msg['from']['first_name'])
            credit['debtor'] = {'id': debtor,
                                'first_name': debtor[1:]}
        else:
            log.logging.warning('User mentioned incorrectly (missing @): %s' % debtor)
            raise RuntimeError(no_user_mentioned_text % msg['from']['first_name'])

    return credit


def extract_credit_id_from_undo_request(msg):
    """Extracts the id of the credit indicated by the undo request.

    :param msg: dict, Telegram message
    :return: integer, id of the credit to be removed
    """
    pattern = r'^%s (?P<id>[0-9]+)$' % commands['undo']
    match = re.match(pattern, msg['text'])
    if match is None:
        log.logging.warning('Invalid format for undo request')
        raise RuntimeError(invalid_undo_request_format_text % msg['from']['first_name'])
    return int(match.groupdict()['id'])


def extract_related_user_from_stats_request(msg):
    """Extract mentioned user from a stats request.

    :param msg: dict, Telegram message
    :return: dict, Telegram user object
    """
    try:
        mention = next(
            entity for entity in msg['entities'] if entity['type'] == 'text_mention' or entity['type'] == 'mention')
    except (StopIteration, KeyError):
        log.logging.debug('Stats request without user')
        return None

    if mention['type'] == 'text_mention':
        return mention['user']
    else:
        # We allow Umlaute in a word or name
        word_chars = 'A-Za-z\s\xe4\xc4\xf6\xd6\xfc\xdc\xdf'
        pattern = '^%s (?P<user>[@%s]+)$' % (commands['stats'], word_chars)
        match = re.match(pattern, msg['text'])
        if match is None:
            log.logging.warning('Invalid stats format: %s' % msg)
            raise RuntimeError(invalid_stats_request_format_text % msg['from']['first_name'])
        return {'id': match.groupdict()['user'],
                'first_name': match.groupdict()['user'][1:]}


def pretty_print(json_obj):
    """Pretty print a json serializable object.

    :param json_obj: json serializable object
    :return: None
    """
    print json.dumps(json_obj, indent=2)


def pretty_string_for_many_credits(credits):
    """Convert information from multiple credits to a string.

    :param credits: list, many credit objects (see message.extract_credit)
    :return: string, contains information of all credits in a pretty format
    """
    credit_strings = []
    for credit in credits:
        credit_strings.append('%s -> %s %.2f "%s" (#%d)' % (
            credit['donor']['first_name'], credit['debtor']['first_name'], credit['amount'], credit['description'],
            credit['id']))
    return '\n'.join(credit_strings)


def new_processor(bot):
    """Create a callback method for processing Telegram messages.

    :param bot: telepot.Bot, The bot that under which this callback will be registered (for answering messages)
    :return: function, callback method for processing Telegram messages
    """

    def process(msg):
        """Processes a Telegram message.
        Sends an appropriate answer in each case. Currently the following cases are respected:
            * Message that indicates a credit
            * Message that indicates an info request
            * Message that indicates a new user that joined the group
            * Message that indicates a user that left the group (no answer in this case)

        If the message does not match any of the above cases the bot will reply with a message that it didn't understand
        the request.

        :param msg: dict, Telegram message
        :return: None
        """
        if is_credit(msg):
            log.logging.debug('Received credit')
            try:
                credit = extract_credit(msg)
            except RuntimeError as err:
                bot.sendMessage(msg['chat']['id'], err.message)
            else:
                pretty_print(credit)
                database.add_credit_if_missing(credit)
                response = credit_success_text % (
                    msg['from']['first_name'], credit['amount'], credit['debtor']['first_name'], credit['description'])
                response += '\n' + undo_info % (msg['message_id'])
                bot.sendMessage(msg['chat']['id'], response)
        elif is_undo(msg):
            log.logging.debug('Received undo request')
            try:
                credit_id = extract_credit_id_from_undo_request(msg)
            except RuntimeError as err:
                bot.sendMessage(msg['chat']['id'], err.message)
            else:
                try:
                    credit = database.remove_credit_is_donor_matches(credit_id, msg['from'])
                except RuntimeError as err:
                    bot.sendMessage(msg['chat']['id'], err.message)
                else:
                    bot.sendMessage(msg['chat']['id'], undo_success_text % (msg['from']['first_name'], credit['amount'],
                                                                            credit['debtor']['first_name']))
        elif is_stats(msg):
            log.logging.debug('Received stats request')
            user = extract_related_user_from_stats_request(msg)
            response = pretty_string_for_many_credits(database.get_all_credits(user=user))
            if not response:
                response = no_credits_for_user % user['first_name']
            bot.sendMessage(msg['chat']['id'], response)
        elif is_bill_request(msg):
            log.logging.debug('Received bill request')
            response = finance.pretty_string_for_many_transfers(
                finance.process_many_credits(database.get_all_credits()))
            bot.sendMessage(msg['chat']['id'], response)
        elif is_help_request(msg):
            log.logging.debug('Received help request')
            bot.sendMessage(msg['chat']['id'], help_text % msg['from']['first_name'])
        elif is_new_user(msg):
            log.logging.debug('New user joined group: %s' % msg['new_chat_member']['first_name'])
            bot.sendMessage(msg['chat']['id'], greeting_text % msg['new_chat_member']['first_name'])
        elif is_user_left(msg):
            log.logging.debug('User left group: %s' % msg['left_chat_member']['first_name'])
        else:
            log.logging.debug('Unknown command')
            bot.sendMessage(msg['chat']['id'], unknown_request_text % msg['from']['first_name'])

    return process
