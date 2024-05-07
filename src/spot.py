
class Spot():
    symbol: str
    quantity: float

    value: float
    profit: float

    def __init__(self, s: str, q: float = 0.0):
        self.symbol = s
        self.quantity = q
        self.value = 0.0
        self.profit = 0.0

    def __repr__(self):
        return f'Spot[s={self.symbol},q={self.quantity},v={self.value},p={self.profit}]'

    def to_json(self):
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'value': self.value,
            'profit': self.profit,
        }

    def to_str(self) -> str:
        return f'{self.quantity:.2f} {self.symbol}'

    def add_spot(self, spot: 'Spot'):
        self.quantity += spot.quantity

    def sub_spot(self, spot: 'Spot'):
        self.quantity -= spot.quantity
