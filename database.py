import tinydb

import config
import log


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
