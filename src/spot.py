
class Spot():
    symbol: str
    quantity: float
    trx_count: int
    transactions = list

    value: float # TODO move to different class
    profit: float
    price: float

    def __init__(self, s: str, q: float = 0.0):
        self.symbol = s
        self.quantity = q
        self.trx_count = 0
        self.transactions = []

        self.value = None
        self.profit = None
        self.price = None

    def __repr__(self):
        return f'Spot[s={self.symbol},q={self.quantity},v={self.value},p={self.profit}]'

    def to_json(self):
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'trx_count': self.trx_count,
            'trx_len': len(self.transactions),
            'transactions': self.transactions,

            'value': self.value,
            'profit': self.profit,
        }

    def to_str(self) -> str:
        return f'{self.quantity:.2f} {self.symbol}'

    def add_trx_count(self, c: int = 1):
        self.trx_count += c

    def add_spot(self, spot: 'Spot'):
        self.quantity += spot.quantity

    def sub_spot(self, spot: 'Spot'):
        self.quantity -= spot.quantity


class Holding(Spot):
    quote: float
    transactions: list

    def __init__(self, s: str, q: float = 0.0):
        super().__init__(s, q)

        self.quote = 0.0
        self.value = 0.0
        self.profit = 0.0


    def to_json(self):
        return {
            **super().to_json(),
            #'symbol': self.symbol,
            #'quantity': self.quantity,
            'quote': self.quote,
            #'value': self.value,
            #'profit': self.profit,
            #'trx_count': self.trx_count,
            #'transactions': len(self.transactions),
        }
