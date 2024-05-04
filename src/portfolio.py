
from json import dumps
from spot import Spot
from pair import Pair
from transaction import Transaction
from apptypes import Quotes
from json_helper import ComplexEncoder

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
    # buy_costs: dict[str, ]
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
        # self.buy_costs = {}
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
        print(f'-> add_pair({self.name},{tpair},{ttype})')

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
            # print(f'-> pair: {pair}')

            if pair.sell_spot.symbol not in self.holdings:
                self.holdings[pair.sell_spot.symbol] = Spot(pair.sell_spot.symbol)

            if pair.buy_spot.symbol not in self.holdings:
                self.holdings[pair.buy_spot.symbol] = Spot(pair.buy_spot.symbol)

        # print(f'-> self.holdings: {self.holdings}')

        # print(f'------- holdings -------')
        # print(self.holdings)
        # print(dumps(self.holdings, indent=2))
        # print(f'------------------------')

        for sym, holding in self.holdings.items():
            # print(f'-> holding: {sym}, {holding}')

            for pair_id, pair in self.pairs.items():
                # print(f'->    pair: {pair_id}, {pair}')

                if sym == pair.sell_spot.symbol:
                    # print(f'->      sell_spot: {pair.sell_spot}')
                    holding.sub_spot(pair.sell_spot)

                elif sym == pair.buy_spot.symbol:
                    # print(f'->      buy_spot: {pair.buy_spot}')
                    holding.add_spot(pair.buy_spot)

        # print('------- holdings -------')
        # print(dumps(self.holdings, indent=2, cls=ComplexEncoder))
        # print('------------------------')

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
