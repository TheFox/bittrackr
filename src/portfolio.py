
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
    pairs: dict[str, Pair]
    holdings: dict[str, Spot]

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
        self.pairs = {}

    def add_portfolio(self, portfolio: 'Portfolio'):
        self.subs.append(portfolio)

    def add_transaction(self, transaction: Transaction):
        print(f'-> add_transaction({transaction.ttype})')

        self.add_pair(transaction.pair, transaction.ttype)

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

    def add_pair(self, tpair: Pair, ttype: str):
        if tpair.name in self.pairs:
            # print('-> already in portfolio pairs')
            ppair = self.pairs[tpair.name]
        else:
            # print('-> new portfolio pair')
            ppair = Pair(tpair.name)
            ppair.sell_spot = Spot(tpair.sell_spot.symbol)
            ppair.buy_spot = Spot(tpair.buy_spot.symbol)

            self.pairs[ppair.name] = ppair

        print(f'-> ppair: {ppair}')

        if ttype == 'buy':
            ppair.add_buy(tpair)

        elif ttype == 'sell':
            ppair.add_sell(tpair)

        if self.parent is not None:
            self.parent.add_pair(tpair, ttype)

    def calc(self):
        # print(f'-> calc({self.name})')

        self.holdings = {}
        for pair_id, pair in self.pairs.items():
            # print(f'-> pair {pair_id}=>{pair}')

            if pair.sell_spot.symbol not in self.holdings:
                self.holdings[pair.sell_spot.symbol] = Spot(pair.sell_spot.symbol)

            if pair.buy_spot.symbol not in self.holdings:
                self.holdings[pair.buy_spot.symbol] = Spot(pair.buy_spot.symbol)

        # print(f'-> self.holdings={self.holdings}')

        for sym, spot in self.holdings.items():
            for pair_id, pair in self.pairs.items():

                if sym == pair.sell_spot.symbol:
                    # print(f'-> sym({sym}) is sell spot: {pair.sell_spot}')

                    spot.sub_q(pair.sell_spot.quantity)

                elif sym == pair.buy_spot.symbol:
                    # print(f'-> sym({sym}) is buy spot: {pair.buy_spot}')

                    spot.add_q(pair.buy_spot.quantity)

        for sub_portfolio in self.subs:
            sub_portfolio.calc()
