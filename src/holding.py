
from spot import Spot
from transaction import Transaction

class Holding(Spot):
    quote: float
    transactions: list[Transaction]

    def __init__(self, s: str, q: float = 0.0):
        super().__init__(s, q)

        self.quote = 0.0
        self.value = 0.0
        self.profit = 0.0

    def to_json(self):
        return {
            **super().to_json(),
            'quote': self.quote,
        }
