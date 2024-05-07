
from spot import Spot

class Pair():
    name: str
    sell_spot: Spot
    buy_spot: Spot
    transactions: list

    def __init__(self, name: str = None):
        self.name = name
        self.sell_spot = None
        self.buy_spot = None
        self.transactions = []

    def __repr__(self):
        return f'Pair[s={self.sell_spot},b={self.buy_spot},t={len(self.transactions)}]'

    def to_json(self):
        return {
            'name': self.name,
            'sell_spot': self.sell_spot,
            'buy_spot': self.buy_spot,
            'transactions': self.transactions,
        }

    def _init_pair(self, pair: 'Pair'):
        if self.sell_spot is None:
            self.sell_spot = Spot(s=pair.sell)

        if self.buy_spot is None:
            self.buy_spot = Spot(s=pair.buy)

    def add_buy(self, pair: 'Pair'):
        self._init_pair(pair)

        self.sell_spot.add_spot(pair.sell_spot)
        self.buy_spot.add_spot(pair.buy_spot)

    def add_sell(self, pair: 'Pair'):
        self._init_pair(pair)

        self.sell_spot.sub_spot(pair.sell_spot)
        self.buy_spot.sub_spot(pair.buy_spot)

    def add_transaction(self, transaction):
        self.transactions.append(transaction)
