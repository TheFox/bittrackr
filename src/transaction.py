
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
    location: str|None
    note: str|None
    pair: Pair

    def __init__(self, pair: str, d: dict):
        self.pair_s = pair
        self.date = None
        self.ttype = None
        self.price = 0.0
        self.quantity = 0.0
        self.location = None
        self.note = None

        sell_symbol, buy_symbol = self.pair_s.split('/')
        self.sell_symbol = sell_symbol
        self.buy_symbol = buy_symbol

        for key, value in d.items():
            setattr(self, key, value)

        self.ttype = getattr(self, 'type')

        pair = Pair()
        pair.name = self.pair_s
        pair.sell = self.sell_symbol
        pair.buy = self.buy_symbol
        pair.price = self.price
        pair.quantity = self.quantity

        q = self.price * self.quantity
        pair.sell_spot = Spot(s=self.sell_symbol,q=q)

        pair.buy_spot = Spot(s=self.buy_symbol,q=self.quantity)

        self.pair = pair

        if self.ttype == 'buy':
            pass
            # q = self.price * self.quantity
            # sell_spot = Spot(s=self.sell_symbol, q=q)
            # self.pair.add_spot(sell_spot)

            # buy_spot = Spot(s=self.buy_symbol, q=self.quantity)
            # self.pair.add_spot(buy_spot)
        elif self.ttype == 'sell':
            pass
            # sell_spot = Spot(s=self.sell_symbol, q=self.quantity)
            # self.pair.add_spot(sell_spot)

            # q = self.price * self.quantity
            # buy_spot = Spot(s=self.buy_symbol, q=q)
            # self.pair.add_spot(buy_spot)
