
from spot import Spot
from pair import Pair
from transaction import Transaction

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
            self.add_pair(transaction.pair)

        elif transaction.ttype == 'sell':
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

        else:
            print('-> new portfolio pair')
            ppair = Pair()
            ppair.name = tpair.name
            ppair.sell = tpair.sell
            ppair.buy = tpair.buy
            self.pairs[ppair.name] = ppair

        self.pairs[tpair.name].calc_cost()

        if self.parent is not None:
            self.parent.add_pair(tpair, d)
