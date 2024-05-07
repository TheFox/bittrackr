
from spot import Spot
from pair import Pair
from transaction import Transaction
from apptypes import Quotes

class Holding(Spot):
    quote: float
    value: float
    transactions: list[Transaction]

    def __init__(self, s: str, q: float = 0.0):
        super().__init__(s, q)
        self.quote = 0.0
        self.value = 0.0
        self.transactions = []

    def to_json(self):
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'quote': self.quote,
            'value': self.value,
            'transactions': self.transactions,
        }

    def add_transaction(self, transaction: Transaction):
        self.transactions.append(transaction)

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
    holdings: dict[str, Holding]

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
        self.holdings = {}

    def to_json(self):
        return {
            'name': self.name,
            'pairs': self.pairs,
            'holdings': self.holdings,
        }

    def add_portfolio(self, portfolio: 'Portfolio'):
        self.subs.append(portfolio)

    def add_transaction(self, transaction: Transaction):
        ppair = self.add_pair(transaction.pair, transaction.ttype)
        ppair.add_transaction(transaction)

        self.transactions_c += 1
        self.sell_symbols.add(transaction.sell_symbol)
        self.buy_symbols.add(transaction.buy_symbol)

        if self.parent is not None:
            self.parent.add_transaction(transaction)

    def add_pair(self, tpair: Pair, ttype: str) -> Pair:
        # print(f'-> add_pair({self.name},{tpair},{ttype})')

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

        return ppair

    def calc(self):
        self.holdings = {}
        for pair_id, pair in self.pairs.items():

            if pair.sell_spot.symbol not in self.holdings:
                holding = Holding(pair.sell_spot.symbol)
                holding.transactions = pair.transactions

                self.holdings[pair.sell_spot.symbol] = holding

            if pair.buy_spot.symbol not in self.holdings:
                holding = Holding(pair.buy_spot.symbol)
                holding.transactions = pair.transactions

                self.holdings[pair.buy_spot.symbol] = holding

        for sym, holding in self.holdings.items():
            for pair_id, pair in self.pairs.items():
                if sym == pair.sell_spot.symbol:
                    holding.sub_spot(pair.sell_spot)
                elif sym == pair.buy_spot.symbol:
                    holding.add_spot(pair.buy_spot)

        for sub_portfolio in self.subs:
            sub_portfolio.calc()

    def quotes(self, quotes: Quotes):
        for sym, spot in self.holdings.items():
            if spot.symbol in quotes:
                quote = quotes[spot.symbol]
                spot.quote = quote
                spot.value = quote * spot.quantity

        for sub_portfolio in self.subs:
            sub_portfolio.quotes(quotes)
