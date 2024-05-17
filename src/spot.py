
class Spot():
    symbol: str
    quantity: float
    trx_count: int

    value: float # TODO move to different class
    profit: float
    price: float

    def __init__(self, s: str, q: float = 0.0):
        self.symbol = s
        self.quantity = q
        self.trx_count = 0

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
