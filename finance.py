import database
import log


def create_transfer_from_credit(credit):
    """Creates a transfer object.
    Transfer objects are represented by dicts and contain the following keys:
        * from: sender
        * to: recipient
        * amount: amount

    :param credit: dict, credit object (see message.extract_credit)
    :return: dict, transfer object
    """
    return {
        'from': credit['debtor'],
        'to': credit['donor'],
        'amount': credit['amount'],
    }


def process_many_credits(credits):
    """Convert a list of credits to a list of transfers.

    :param credits: list, contains credit objects (see message.extract_credit)
    :return: list, contains transfer objects (see finance.create_transfer)
    """

    def rotate_transfers_positive(transfers):
        """Rotates sender and recipient of all transfers that have a negative amount so they evaluate positive finally.

        :param transfers: list, contains transfer objects (see finance.create_transfer)
        :return: list, contains transfer objects (see finance.create_transfer), all having positive amounts
        """
        return map(lambda t: {'from': t['to'], 'to': t['from'], 'amount': -t['amount']} if t['amount'] < 0. else t,
                   transfers)

    def merge_transfers_if_possible(t1, t2):
        """Merge transfer t2 into transfer t1 if they involve the same parties.
        Raises a ValueError if they two transfers involve different parties.

        :param t1: transfer object (see finance.create_transfer)
        :param t2: transfer object (see finance.create_transfer)
        :return: t1, updated transfer
        """
        if {t1['from']['id'], t1['to']['id']} == {t2['from']['id'], t2['to']['id']}:
            # Involve the same parties
            if t1['from'] == t2['from']:
                t1['amount'] += t2['amount']
            else:
                t1['amount'] -= t2['amount']
            return t1
        else:
            raise ValueError('Transfers do not involve the same parties')

    transfers = map(create_transfer_from_credit, credits)
    merged_transfers = []
    for transfer in transfers:
        for merged_transfer in merged_transfers:
            try:
                merge_transfers_if_possible(merged_transfer, transfer)
            except ValueError:
                # Didn't involve the same parties
                pass
            else:
                # Involved the same parties -> got merged
                break
        else:
            # No merge -> use as seed for subsequent transfers
            merged_transfers.append(transfer)

    final_transfers = rotate_transfers_positive(merged_transfers)

    return final_transfers


def pretty_string_for_many_transfers(transfers):
    """Convert information from multiple transfers to a string.

    :param transfers: list, many transfer objects (see finance.create_transfer)
    :return: string, contains information of all transfers in a pretty format
    """
    transfer_strings = []
    for transfer in transfers:
        # transfer_strings.append('%s (%s) -> %s (%s) %.2f' % (
        #     transfer['from']['first_name'], transfer['from']['id'],
        #     transfer['to']['first_name'], transfer['to']['id'],
        #     transfer['amount']))
        transfer_strings.append('%s -> %s %.2f' % (transfer['from']['first_name'], transfer['to']['first_name'],
                                                   transfer['amount']))
    return '\n\n'.join(transfer_strings)
