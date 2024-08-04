
from typing import Optional
from spot import Spot
from pair import Pair
from datetime import datetime

class Transaction():
    source: str
    pair_s: str
    symbol: str
    sell_symbol: Optional[str]
    buy_symbol: Optional[str]
    date: Optional[str]
    ttype: Optional[str]
    price: Optional[float]
    cprice: Optional[float]
    quantity: float
    fee: Optional[Spot]
    location: Optional[str]
    note: Optional[str]
    pair: Optional[Pair]
    is_pair: bool
    spot: Optional[Spot]
    profit: Optional[float]
    state: Optional[str]
    ignore: Optional[bool]
    target: Optional[str]
    target_f: Optional[float]
    target_spot: Optional[Spot]

    def __init__(self, source: str, pair: str, d: dict):
        self.source = source
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
        self.profit = None
        self.state = None
        self.ignore = None
        self.target = None
        self.target_f = None
        self.target_spot = None

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

        if self.target is not None:
            self.target_f = float(self.target)

        if self.fee is not None:
            if len(self.fee) == 2:
                self.fee = Spot(s=self.fee[1], q=self.fee[0])
            else:
                self.fee = None

        if self.is_pair:
            pair: Pair = Pair(self.pair_s)

            # print(f'self={self}')
            # print(f'self.price={self.price}')
            # print(f'self.quantity={self.quantity}')
            # print(f'-------')

            q = self.price * self.quantity
            pair.sell_spot = Spot(s=self.sell_symbol, q=q)

            pair.buy_spot = Spot(s=self.buy_symbol, q=self.quantity)

            self.pair = pair
        else:
            self.spot = Spot(s=self.pair_s, q=self.quantity)

        # print(f'self={self}')

        if self.ttype == 'buy-order' or self.ttype == 'sell-order':
            year = datetime.now().year
            self.date = f'{year}-12-31 23:59'

    def __repr__(self):
        return f'Transaction[{self.pair_s},t={self.ttype},p={self.pair},s={self.spot}]'

    def to_json(self):
        return {
            'pair_name': self.pair_s,
            'pair': self.pair,
            'ttype': self.ttype,
            'price': self.price,
            'quantity': self.quantity,
            'spot': self.spot,
            'profit': self.profit,
        }
