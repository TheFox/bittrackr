
from spot import Spot

class Pair():
    name: str
    sell: str
    buy: str
    price: float
    prices: list[float]
    quantity: float
    cost_s: str
    spots: list
    sell_spot: Spot
    buy_spot: Spot

    def __init__(self):
        self.price = 0.0
        self.prices = []
        self.quantity = 0.0
        self.cost_s = 'NOTSET'
        self.spots = []
        self.sell_spot = None
        self.buy_spot = None

    def __repr__(self):
        return f'Pair[{self.sell_spot},{self.buy_spot}]'

    def add_spot(self, spot: Spot):
        self.spots.append(spot)

    def _init_pair(self, pair: 'Pair'):
        print(f'-> _init_pair -> {pair}')

        if self.sell_spot is None:
            self.sell_spot = Spot(s=pair.sell)

        if self.buy_spot is None:
            self.buy_spot = Spot(s=pair.buy)

    def add_buy(self, pair: 'Pair'):
        print(f'-> add_buy -> {pair}')
        self._init_pair(pair)

        #self.sell_spot.add_q(pair.price * pair.quantity)
        #self.buy_spot.add_q(pair.quantity)

        self.sell_spot.add_spot(pair.sell_spot)
        self.buy_spot.add_spot(pair.buy_spot)

    def add_sell(self, pair: 'Pair'):
        print(f'-> add_sell -> {pair}')
        self._init_pair(pair)

        # self.sell_spot.sub_q(pair.price * pair.quantity)
        # self.buy_spot.sub_q(pair.quantity)

        self.sell_spot.sub_spot(pair.sell_spot)
        self.buy_spot.sub_spot(pair.buy_spot)

    def calc_cost(self):
        print('-> calc_cost')
        # cost = self.price * self.quantity
        # self.cost_s = f'{cost:.2f} {self.sell}'
