
class Spot():
    symbol: str
    quantity: float

    def __init__(self, s: str, q: float = 0.0):
        self.symbol = s
        self.quantity = q

    def __repr__(self):
        return f'Spot[s={self.symbol},q={self.quantity}]'

    def add_q(self, q: float):
        self.quantity += q

    def sub_q(self, q: float):
        self.quantity -= q

    def add_spot(self, spot: 'Spot'):
        self.quantity += spot.quantity

    def sub_spot(self, spot: 'Spot'):
        self.quantity -= spot.quantity

    def calc_value(self, quotes: dict) -> float:
        if not self.symbol in quotes:
            return 0.0
        return quotes[self.symbol] * self.quantity
