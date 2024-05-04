
class Spot():
    symbol: str
    quantity: float

    def __init__(self, s: str, q: float = 0.0):
        self.symbol = s
        self.quantity = q

    def __repr__(self):
        return f'Spot[s={self.symbol},q={self.quantity}]'

    def to_json(self):
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
        }

    def add_spot(self, spot: 'Spot'):
        self.quantity += spot.quantity

    def sub_spot(self, spot: 'Spot'):
        self.quantity -= spot.quantity
