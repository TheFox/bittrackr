
from spot import Spot
from transaction import Transaction

class Holding(Spot):
    quote: float
    value: float

    def __init__(self, s: str, q: float = 0.0):
        super().__init__(s, q)

        self.quote = 0.0
        self.value = 0.0

    def to_json(self):
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'quote': self.quote,
            'value': self.value,
            'trx_count': self.trx_count,
        }
