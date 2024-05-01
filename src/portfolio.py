
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
    # cost: float
    location: str|None
    note: str|None
    # pair: Pair

    def __init__(self, pair: str, d: dict):
        self.pair_s = pair
        self.date = None
        self.ttype = None
        self.price = 0.0
        self.quantity = 0.0
        # self.cost = 0.0
        self.location = None
        self.note = None

        sell_symbol, buy_symbol = self.pair_s.split('/')
        self.sell_symbol = sell_symbol
        self.buy_symbol = buy_symbol

        for key, value in d.items():
            setattr(self, key, value)

        self.ttype = getattr(self, 'type')

        self.pair = Pair()
        self.pair.name = self.pair_s
        self.pair.sell = self.sell_symbol
        self.pair.buy = self.buy_symbol
        #self.pair.price = self.price
        #self.pair.quantity = self.quantity
        #self.pair.calc_cost()

        if self.ttype == 'buy':
            q = self.price * self.quantity
            sell_spot = Spot(s=self.sell_symbol, q=q)
            self.pair.add_spot(sell_spot)

            buy_spot = Spot(s=self.buy_symbol, q=self.quantity)
            self.pair.add_spot(buy_spot)
        elif self.ttype == 'sell':
            sell_spot = Spot(s=self.sell_symbol, q=self.quantity)
            self.pair.add_spot(sell_spot)

            q = self.price * self.quantity
            buy_spot = Spot(s=self.buy_symbol, q=q)
            self.pair.add_spot(buy_spot)



class Portfolio():
    parent: 'Portfolio'
    name: str
    level: int
    symbols: set
    sell_symbols: set
    buy_symbols: set
    fees: float
    transactions: list[Transaction]
    transactions_c: int
    subs: list['Portfolio']
    quantity: dict[str, Spot]
    pairs: dict[str, Pair]

    def __init__(self, name: str, parent: None = None):
        self.name = name
        if parent is not None:
            self.level = parent.level + 1
        else:
            self.level = 0
        self.parent = parent
        self.symbols = set()
        self.sell_symbols = set()
        self.buy_symbols = set()
        self.transactions = []
        self.transactions_c = 0
        self.subs = []
        self.quantity = {}
        self.pairs = {}

    def add_portfolio(self, portfolio: 'Portfolio'):
        self.subs.append(portfolio)

    def add_transaction(self, transaction: Transaction):
        print(f'-> add_transaction({transaction.ttype})')
        if transaction.ttype == 'buy':
            q = transaction.price * transaction.quantity
            self.add_quantity(transaction.sell_symbol, q, -1)

            self.add_quantity(transaction.buy_symbol, transaction.quantity)

            self.add_pair(transaction.pair)

        elif transaction.ttype == 'sell':
            q = transaction.price * transaction.quantity
            self.add_quantity(transaction.sell_symbol, q)

            self.add_quantity(transaction.buy_symbol, transaction.quantity, -1)

            self.add_pair(transaction.pair, -1)

        else:
            raise ValueError(f'Unkown transaction ttype: {transaction.ttype}')

        self.transactions.append(transaction)

        self.count_transactions()
        self.count_sell_symbols(transaction.sell_symbol)
        self.count_buy_symbols(transaction.buy_symbol)

    def count_transactions(self):
        # print(f'-> count_transactions({self.name})')
        self.transactions_c += 1

        if self.parent is not None:
            self.parent.count_transactions()

    def count_sell_symbols(self, symbol: str):
        # print(f'-> count_sell_symbols({self.name}, {symbol})')
        self.sell_symbols.add(symbol)

        if self.parent is not None:
            self.parent.count_sell_symbols(symbol)

    def count_buy_symbols(self, symbol: str):
        # print(f'-> count_buy_symbols({self.name}, {symbol})')
        self.buy_symbols.add(symbol)

        if self.parent is not None:
            self.parent.count_buy_symbols(symbol)

    def add_quantity(self, symbol: str, q: float, d: int = 1):
        # print(f'-> add_quantity({self.name}, {symbol}, {q}, {d})')

        if symbol not in self.quantity:
            self.quantity[symbol] = Spot(s=symbol)

        self.quantity[symbol].add_q(q * d)

        if self.parent is not None:
            self.parent.add_quantity(symbol, q, d)

    def add_pair(self, tpair: Pair, d: int = 1):
        q = tpair.quantity * d
        print(f'-> add_pair {self.name} n={tpair.name} q={tpair.quantity}/{q} d={d}')

        if tpair.name in self.pairs:
            print('-> already in portfolio pairs')
            #self.pairs[tpair.name].quantity += q
            self.pairs[tpair.name].calc_cost()
        else:
            print('-> new portfolio pair')
            ppair = Pair()
            ppair.name = tpair.name
            ppair.sell = tpair.sell
            ppair.buy = tpair.buy
            self.pairs[ppair.name] = ppair

        if self.parent is not None:
            self.parent.add_pair(tpair, d)
