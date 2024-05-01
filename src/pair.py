
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

    def __init__(self):
        self.price = 0.0
        self.prices = []
        self.quantity = 0.0
        self.cost_s = 'NOTSET'
        self.spots = []

    def add_spot(self, spot: Spot):
        self.spots.append(spot)

    def calc_cost(self):
        print('-> calc_cost')
        # cost = self.price * self.quantity
        # self.cost_s = f'{cost:.2f} {self.sell}'
