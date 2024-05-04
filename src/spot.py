
class Spot():
    symbol: str
    quantity: float

    quote: float

    # Current Value based on quote.
    value: float

    avg: list['Spot']

    avg_s: str

    def __init__(self, s: str, q: float = 0.0):
        self.symbol = s
        self.quantity = q
        self.quote = None
        self.value = None
        self.avg = []
        self.avg_s = None

    def __repr__(self):
        return f'Spot[s={self.symbol},q={self.quantity},a={self.avg_s}]'

    def to_json(self):
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'quote': self.quote,
            'value': self.value,
            'avg': self.avg,
            'avg_s': self.avg_s,
        }

    def add_spot(self, spot: 'Spot'):
        self.quantity += spot.quantity

    def sub_spot(self, spot: 'Spot'):
        self.quantity -= spot.quantity
