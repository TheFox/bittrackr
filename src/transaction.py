
from spot import Spot
from pair import Pair

class Transaction():
    pair_s: str
    sell_symbol: str
    buy_symbol: str
    date: str|None
    ttype: str|None
    price: float
    quantity: float
    fee: Spot
    location: str|None
    note: str|None
    pair: Pair

    def __init__(self, pair: str, d: dict):
        self.pair_s = pair
        self.date = None
        self.ttype = None
        self.price = 0.0
        self.quantity = 0.0
        self.fee = None
        self.location = None
        self.note = None

        sell_symbol, buy_symbol = self.pair_s.split('/')
        self.sell_symbol = sell_symbol
        self.buy_symbol = buy_symbol

        for key, value in d.items():
            setattr(self, key, value)

        self.ttype = getattr(self, 'type')
        #print(f'-> Transaction({self.ttype}) fee: {self.fee}')

        if self.fee is not None:
            if len(self.fee) == 2:
                self.fee = Spot(s=self.fee[1], q=self.fee[0])
            else:
                self.fee = None


        pair: Pair = Pair(self.pair_s)

        q = self.price * self.quantity
        pair.sell_spot = Spot(s=self.sell_symbol, q=q)

        pair.buy_spot = Spot(s=self.buy_symbol, q=self.quantity)

        self.pair = pair

    def __repr__(self):
        return f'Transaction[{self.pair_s},{self.ttype},{self.price},{self.quantity}]'

    def to_json(self):
        return {
            'pair': self.pair_s,
            'type': self.ttype,
            'price': self.price,
            'quantity': self.quantity,
        }
