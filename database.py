import tinydb

import config
import log


credit_does_not_exist_text = "Sorry %s,\nbut this credit doesn't exist."
credit_does_not_belong_to_you_text = "Sorry %s,\nbut this credit doesn't belong to you. Ask %s to undo it for you."

db_credits = tinydb.TinyDB(config.config['db.credits.path'])


def add_credit_if_missing(credit):
    """Register the credit in the database if it is not yet stored.

    :param credit: dict, see message.extract_credit
    :return: None
    """
    query = tinydb.Query()
    if db_credits.contains(query.id == credit['id']):
        log.logging.warning('Credit already registered in database: %s' % credit)
        return
    db_credits.insert(credit)


def remove_credit_is_donor_matches(credit_id, issuer):
    """Removes a credit if it belongs to the person that issued the removal.
    Belonging here means that the person is the donor of the credit.

    :param credit_id: integer, message_id of the Telegram message that contained this credit
    :param issuer: dict, Telegram user object, the person who issued the removal
    :return: dict, credit object (see message.extract_credit)
    """
    query = tinydb.Query()
    if not db_credits.contains(query.id == credit_id):
        log.logging.warning('Tried to remove credit that is not registered')
        raise RuntimeError(credit_does_not_exist_text % issuer['first_name'])
    credit = db_credits.search(query.id == credit_id)[0]
    if credit['donor']['id'] != issuer['id']:
        log.logging.warning('%s tried to remove credit #%d that belongs to %s' % (issuer, credit_id, credit['donor']))
        raise RuntimeError(credit_does_not_belong_to_you_text % (issuer['first_name'], credit['donor']['first_name']))
    db_credits.remove(query.id == credit_id)
    return credit


def get_all_credits(user):
    """Returns all credits in the database.

    :param user: dict, Telegram user object
    :return: list, containing all credit objects (see message.extract_credit)
    """
    query = tinydb.Query()
    if user is None:
        return db_credits.search(query.id >= 0)
    else:
        return db_credits.search(query.donor == user) + db_credits.search(query.debtor == user)
