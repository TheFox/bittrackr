
from holding import Holding
from transaction import Transaction

def sort_holdings(item: tuple[str, Holding]):
    value = item[1].value
    if value is None:
        return 0.0
    return value

def sort_transactions(item: Transaction):
    return item.date
