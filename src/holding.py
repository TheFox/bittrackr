
from spot import Spot
from transaction import Transaction

class Holding(Spot):
    quote: float
    value: float
    #transactions: list[Transaction]

    def __init__(self, s: str, q: float = 0.0):
        super().__init__(s, q)

        self.quote = 0.0
        self.value = 0.0

        #self.trx_count = 0
        #self.transactions = []

    def to_json(self):
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'quote': self.quote,
            'value': self.value,
            'trx_count': self.trx_count,
            #'transactions': self.transactions,
        }

    # def add_transactions(self, transactions: list[Transaction]):
    #     self.transactions.extend(transactions)
