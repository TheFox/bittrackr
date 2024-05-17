
from spot import Spot
from pair import Pair

class Transaction():
    pair_s: str
    symbol: str
    sell_symbol: str|None
    buy_symbol: str|None
    date: str|None
    ttype: str|None
    price: float|None
    cprice: float|None
    quantity: float
    fee: Spot|None
    location: str|None
    note: str|None
    pair: Pair|None
    is_pair: bool
    spot: Spot|None

    def __init__(self, pair: str, d: dict):
        self.pair_s = pair
        self.date = None
        self.ttype = None
        self.price = None
        self.cprice = None
        self.quantity = None
        self.fee = None
        self.location = None
        self.note = None
        self.pair = None
        self.spot = None

        if '/' in self.pair_s:
            self.is_pair = True
            sell_symbol, buy_symbol = self.pair_s.split('/')
            self.sell_symbol = sell_symbol
            self.buy_symbol = buy_symbol
        else:
            self.is_pair = False
            self.sell_symbol = None
            self.buy_symbol = None

        for key, value in d.items():
            setattr(self, key, value)

        self.ttype = getattr(self, 'type')

        if self.fee is not None:
            if len(self.fee) == 2:
                self.fee = Spot(s=self.fee[1], q=self.fee[0])
            else:
                self.fee = None

        if self.is_pair:
            pair: Pair = Pair(self.pair_s)

            print(f'self={self}')
            print(f'self.price={self.price}')
            # print(f'self.quantity={self.quantity}')
            # print(f'-------')

            q = self.price * self.quantity
            pair.sell_spot = Spot(s=self.sell_symbol, q=q)

            pair.buy_spot = Spot(s=self.buy_symbol, q=self.quantity)

            self.pair = pair
        else:
            self.spot = Spot(s=self.pair_s, q=self.quantity)

    def __repr__(self):
        return f'Transaction[{self.pair_s},t={self.ttype},p={self.pair},s={self.spot}]'

    def to_json(self):
        return {
            'pair': self.pair_s,
            'ttype': self.ttype,
            'price': self.price,
            'quantity': self.quantity,
            'pair': self.pair,
            'spot': self.spot,
        }
