
from spot import Spot
from pair import Pair
from transaction import Transaction
from apptypes import Quotes

class Portfolio():
    parent: 'Portfolio'
    name: str
    level: int
    symbols: set
    sell_symbols: set
    buy_symbols: set
    fees: float
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
        self.transactions_c = 0
        self.subs = []
        self.pairs = {}

    def add_portfolio(self, portfolio: 'Portfolio'):
        self.subs.append(portfolio)

    def add_transaction(self, transaction: Transaction):
        self.add_pair(transaction.pair, transaction.ttype)

        self.count_transactions()
        self.count_sell_symbols(transaction.sell_symbol)
        self.count_buy_symbols(transaction.buy_symbol)

    def count_transactions(self):
        self.transactions_c += 1

        if self.parent is not None:
            self.parent.count_transactions()

    def count_sell_symbols(self, symbol: str):
        self.sell_symbols.add(symbol)

        if self.parent is not None:
            self.parent.count_sell_symbols(symbol)

    def count_buy_symbols(self, symbol: str):
        self.buy_symbols.add(symbol)

        if self.parent is not None:
            self.parent.count_buy_symbols(symbol)

    def add_pair(self, tpair: Pair, ttype: str):
        if tpair.name in self.pairs:
            ppair = self.pairs[tpair.name]
        else:
            ppair = Pair(tpair.name)
            ppair.sell_spot = Spot(tpair.sell_spot.symbol)
            ppair.buy_spot = Spot(tpair.buy_spot.symbol)

            self.pairs[ppair.name] = ppair

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
            if pair.sell_spot.symbol not in self.holdings:
                self.holdings[pair.sell_spot.symbol] = Spot(pair.sell_spot.symbol)

            if pair.buy_spot.symbol not in self.holdings:
                self.holdings[pair.buy_spot.symbol] = Spot(pair.buy_spot.symbol)

        for sym, spot in self.holdings.items():
            for pair_id, pair in self.pairs.items():

                if sym == pair.sell_spot.symbol:
                    spot.sub_q(pair.sell_spot.quantity)

                elif sym == pair.buy_spot.symbol:
                    spot.add_q(pair.buy_spot.quantity)

        for sub_portfolio in self.subs:
            sub_portfolio.calc()

    def quotes(self, quotes: Quotes):
        # print(f'-> quotes({self.name})')

        for sym, spot in self.holdings.items():
            # print(f'-> sym {sym} {spot}')

            if spot.symbol in quotes:
                quote = quotes[spot.symbol]
                spot.quote = quote
                spot.value = quote * spot.quantity

        for sub_portfolio in self.subs:
            sub_portfolio.quotes(quotes)
