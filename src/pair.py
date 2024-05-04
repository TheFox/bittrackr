
from spot import Spot

class Pair():
    name: str
    sell_spot: Spot
    buy_spot: Spot

    def __init__(self, name: str = None):
        self.name = name
        self.sell_spot = None
        self.buy_spot = None

    def __repr__(self):
        return f'Pair[{self.sell_spot},{self.buy_spot}]'

    def to_json(self):
        return {
            'name': self.name,
            'sell_spot': self.sell_spot,
            'buy_spot': self.buy_spot,
        }

    def _init_pair(self, pair: 'Pair'):
        if self.sell_spot is None:
            self.sell_spot = Spot(s=pair.sell)

        if self.buy_spot is None:
            self.buy_spot = Spot(s=pair.buy)

    def add_buy(self, pair: 'Pair'):
        # print(f'-> add_buy -> {pair}')
        self._init_pair(pair)

        self.sell_spot.add_spot(pair.sell_spot)
        self.buy_spot.add_spot(pair.buy_spot)

    def add_sell(self, pair: 'Pair'):
        # print(f'-> add_sell -> {pair}')
        self._init_pair(pair)

        self.sell_spot.sub_spot(pair.sell_spot)
        self.buy_spot.sub_spot(pair.buy_spot)
