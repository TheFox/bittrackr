
from apptypes import Quotes
from json_helper import ComplexEncoder
from json import dumps
from spot import Spot
from pair import Pair
from transaction import Transaction
from holding import Holding

class Portfolio():
    parent: 'Portfolio'
    name: str
    level: int
    symbols: set
    sell_symbols: set
    buy_symbols: set
    fees: dict[str, Spot]
    transactions: list[Transaction]
    transactions_c: int
    subs: list['Portfolio']
    pairs: dict[str, Pair]
    spots: dict[str, Spot]
    holdings: dict[str, Holding]

    def __init__(self, name: str, parent: 'Portfolio' = None):
        self.name = name
        if parent is not None:
            self.level = parent.level + 1
        else:
            self.level = 0
        self.parent = parent
        self.symbols = set()
        self.sell_symbols = set()
        self.buy_symbols = set()
        self.fees = {}
        self.fee_value = 0.0
        self.transactions = []
        self.transactions_c = 0
        self.subs = []
        self.pairs = {}
        self.spots = {}
        self.holdings = {}

    def to_json(self):
        return {
            'name': self.name,
            'pairs': self.pairs,
            'holdings': self.holdings,
            'fees': self.fees,
            'fee_value': self.fee_value,
            'spots': self.spots,
        }

    def add_portfolio(self, portfolio: 'Portfolio'):
        self.subs.append(portfolio)

    def add_transaction(self, transaction: Transaction):
        if self.parent is not None:
            self.parent.add_transaction(transaction)

        self.transactions.append(transaction)
        self.transactions_c += 1

        if transaction.fee is not None:
            self.add_fee(transaction.fee)

        # print(f'-> add trx: {transaction}')
        if transaction.is_pair:
            ppair = self.add_pair(transaction.pair, transaction.ttype)
            ppair.add_transaction(transaction)

            self.sell_symbols.add(transaction.sell_symbol)
            self.buy_symbols.add(transaction.buy_symbol)
        else:
            if transaction.spot.symbol in self.spots:
                spot = self.spots[transaction.spot.symbol]
            else:
                spot = Spot(s=transaction.spot.symbol)
                self.spots[transaction.spot.symbol] = spot

            spot.add_trx_count()

            if transaction.ttype == 'in':
                spot.add_spot(transaction.spot)
            elif transaction.ttype == 'out':
                spot.sub_spot(transaction.spot)
            else:
                raise ValueError(f'Unknown Transaction type: {transaction.ttype}')

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
        else:
            raise ValueError(f'Unknown Transaction type: {ttype}')

        return ppair

    def add_fee(self, fee: Spot):
        if fee.symbol in self.fees:
            pfee = self.fees[fee.symbol]
        else:
            pfee = Spot(s=fee.symbol)
            self.fees[fee.symbol] = pfee

        pfee.add_spot(fee)

    def calc(self):
        for sub_portfolio in self.subs:
            sub_portfolio.calc()

        self.holdings = {}
        for pair_id, pair in self.pairs.items():
            # print(f'-> create holdings from pairs {pair}')

            trx_count = len(pair.transactions)

            if pair.sell_spot.symbol not in self.holdings:
                self.holdings[pair.sell_spot.symbol] = Holding(pair.sell_spot.symbol)
            self.holdings[pair.sell_spot.symbol].add_trx_count(trx_count)

            if pair.buy_spot.symbol not in self.holdings:
                self.holdings[pair.buy_spot.symbol] = Holding(pair.buy_spot.symbol)
            self.holdings[pair.buy_spot.symbol].add_trx_count(trx_count)

        for sym, spot in self.spots.items():
            # print(f'-> create holdings from spots {spot}')

            if spot.symbol not in self.holdings:
                self.holdings[spot.symbol] = Holding(spot.symbol)
            self.holdings[spot.symbol].add_trx_count(spot.trx_count)

        # TODO
        #for fee_id, fee in self.fees.items():

        for hsym, holding in self.holdings.items():
            # print(f'-> calc holding: {holding}')

            for pair_id, pair in self.pairs.items():
                if hsym == pair.sell_spot.symbol:
                    holding.sub_spot(pair.sell_spot)
                elif hsym == pair.buy_spot.symbol:
                    holding.add_spot(pair.buy_spot)

            for ssym, spot in self.spots.items():
                if ssym == hsym:
                    holding.add_spot(spot)


    def quotes(self, quotes: Quotes, convert: str):
        # print(f'-> quotes: {quotes}')

        for sub_portfolio in self.subs:
            sub_portfolio.quotes(quotes, convert)

        for transaction in self.transactions:

            if transaction.is_pair:
                print(f'-> calc pair trx: {transaction}')

                pair = transaction.pair

                print(f'->    ck sell_spot: {pair.sell_spot.symbol}=={convert}')
                print(f'->    ck buy_spot:  {pair.buy_spot.symbol}=={convert}')

                if pair.sell_spot.symbol == convert:
                    if pair.buy_spot.symbol not in quotes:
                        raise ValueError(f'Buy Symbol not found in quotes: {pair.buy_spot.symbol}')
                    pair.buy_spot.value = quotes[pair.buy_spot.symbol] * pair.buy_spot.quantity
                    pair.profit = pair.buy_spot.value - pair.sell_spot.quantity
                elif pair.buy_spot.symbol == convert:
                    if pair.sell_spot.symbol not in quotes:
                        raise ValueError(f'Sell Symbol not found in quotes: {pair.sell_spot.symbol}')
                    pair.sell_spot.value = quotes[pair.sell_spot.symbol] * pair.sell_spot.quantity
                    #pair.profit =
                    raise NotImplementedError(f'T1: {pair.sell_spot.value - pair.sell_spot.quantity} T2: {pair.sell_spot.value - pair.buy_spot.quantity}')
                else:
                    pass
                    # TODO: To address this issue, you'll need to provide an additional dictionary to specify the exchange rate between the non-EUR currencies in the pair.
                    # pair.sell_spot.value = quotes[pair.sell_spot.symbol] * pair.sell_spot.quantity
                    pair.buy_spot.value = quotes[pair.buy_spot.symbol] * pair.buy_spot.quantity
                    # pair.profit = pair.sell_spot.value - pair.buy_spot.value

                    # print(f'->    sell_spot={pair.sell_spot}')
                    # print(f'->    buy_spot={pair.buy_spot}')
                    # print(f'->    pair.profit={pair.profit}')

            else:
                spot = transaction.spot
                if spot.symbol not in quotes:
                    raise ValueError(f'Symbol not found in quotes: {spot.symbol}')
                spot.value = quotes[spot.symbol] * spot.quantity
                if transaction.ttype == 'in':
                    spot.profit = spot.value
                elif transaction.ttype == 'out':
                    spot.profit = spot.value * -1
                else:
                    raise ValueError(f'Unknown Transaction type: {transaction.ttype}')

                # print(f'-> calc trx spot transaction: {spot}')

        # print('------- transactions -------')
        # print(dumps(self.transactions, indent=2, cls=ComplexEncoder))
        # print('------------------------')

        # print('------- holdings A -------')
        # print(dumps(self.holdings, indent=2, cls=ComplexEncoder))
        # print('------------------------')

        # Holdings
        for hsym, holding in self.holdings.items():
            # print(f'-> quotes holding: {holding}')

            if holding.symbol not in quotes:
                #raise ValueError(f'Symbol not found in quotes: {holding.symbol}')
                continue

            quote = quotes[holding.symbol]
            holding.quote = quote
            holding.value = quote * holding.quantity

        # print('------- holdings B -------')
        # print(dumps(self.holdings, indent=2, cls=ComplexEncoder))
        # print('------------------------')

        # Fees
        for fee_id, fee in self.fees.items():
            if fee.symbol == convert:
                self.fee_value += fee.quantity
            elif fee.symbol in quotes:
                self.fee_value += fee.quantity * quotes[fee.symbol]
            else:
                raise ValueError(f'Symbol not found in quotes and not in convert: {spot.symbol}')

    def get_convert_symbols(self, convert: str) -> dict[str, list[str]]:
        symbols = {}
        for pair_id, pair in self.pairs.items():
            print(f'-> pair {pair}')

            if pair.sell_spot.symbol != convert and pair.buy_spot.symbol != convert:
                if pair.sell_spot.symbol not in symbols:
                    symbols[pair.sell_spot.symbol] = []

                symbols[pair.sell_spot.symbol].append(pair.buy_spot.symbol)

            elif pair.sell_spot.symbol == convert:
                if pair.sell_spot.symbol not in symbols:
                    symbols[pair.sell_spot.symbol] = []

                symbols[pair.sell_spot.symbol].append(pair.buy_spot.symbol)

            elif pair.buy_spot.symbol == convert:
                if pair.buy_spot.symbol not in symbols:
                    symbols[pair.buy_spot.symbol] = []

                symbols[pair.buy_spot.symbol].append(pair.sell_spot.symbol)

        return symbols
