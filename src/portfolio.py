
from apptypes import ConvertSymbols
from json_helper import ComplexEncoder
from json import dumps
from spot import Spot, Holding
from pair import Pair
from transaction import Transaction
from quotes import Quotes

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
    costs: Spot|None

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
        self.costs = None

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
            spot.transactions.append(transaction)

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
            trx_count = len(pair.transactions)

            if pair.sell_spot.symbol not in self.holdings:
                self.holdings[pair.sell_spot.symbol] = Holding(pair.sell_spot.symbol)

            self.holdings[pair.sell_spot.symbol].add_trx_count(trx_count)
            self.holdings[pair.sell_spot.symbol].transactions.extend(pair.transactions)

            if pair.buy_spot.symbol not in self.holdings:
                self.holdings[pair.buy_spot.symbol] = Holding(pair.buy_spot.symbol)

            self.holdings[pair.buy_spot.symbol].add_trx_count(trx_count)
            self.holdings[pair.buy_spot.symbol].transactions.extend(pair.transactions)

        for sym, spot in self.spots.items():
            if spot.symbol not in self.holdings:
                self.holdings[spot.symbol] = Holding(spot.symbol)

            self.holdings[spot.symbol].add_trx_count(spot.trx_count)
            self.holdings[spot.symbol].transactions.extend(spot.transactions)

        # TODO
        #for fee_id, fee in self.fees.items():

        for hsym, holding in self.holdings.items():

            for pair_id, pair in self.pairs.items():

                if holding.symbol == pair.sell_spot.symbol:
                    holding.sub_spot(pair.sell_spot)

                elif holding.symbol == pair.buy_spot.symbol:
                    holding.add_spot(pair.buy_spot)

            for ssym, spot in self.spots.items():
                if holding.symbol == spot.symbol:
                    holding.add_spot(spot)

    def get_convert_symbols(self, convert: str) -> ConvertSymbols:
        symbols = {}

        def add(sym: str, val: str):
            if sym not in symbols:
                symbols[sym] = []
            if val not in symbols[sym]:
                symbols[sym].append(val)

        # Pairs
        for pair_id, pair in self.pairs.items():
            # print(f'-> pair {pair}')

            if pair.sell_spot.symbol != convert and pair.buy_spot.symbol != convert:
                add(pair.sell_spot.symbol, pair.buy_spot.symbol)

            elif pair.sell_spot.symbol == convert:
                add(pair.sell_spot.symbol, pair.buy_spot.symbol)

            elif pair.buy_spot.symbol == convert:
                add(pair.buy_spot.symbol, pair.sell_spot.symbol)

        # Spots
        for ssym, spot in self.spots.items():
            # print(f'-> spot: {ssym} {spot}')
            add(convert, spot.symbol)

        # Holdings
        for hsym, holding in self.holdings.items():
            if holding.symbol == convert:
                continue
            # print(f'-> quotes holding: {holding}')
            add(convert, holding.symbol)

        # Fees
        for fee_id, fee in self.fees.items():
            if fee.symbol == convert:
                continue
            # print(f'-> fee {fee_id} {fee}')
            add(convert, fee.symbol)

        return symbols

    def quotes(self, quotes: Quotes, convert: str):
        for sub_portfolio in self.subs:
            sub_portfolio.quotes(quotes, convert)

        for transaction in self.transactions:

            if transaction.is_pair:
                pair = transaction.pair

                transaction.cprice = quotes.get(convert, pair.buy_spot.symbol)

                cquote = quotes.get(convert, pair.buy_spot.symbol)

                print()
                print(f'-> transaction type: {transaction.ttype}')
                print(f'-> cquote: {cquote} ({pair.buy_spot.symbol})')

                if pair.sell_spot.symbol == convert:
                    pair.value = cquote * pair.buy_spot.quantity
                    print(f'-> {pair.value}(value) = {cquote}(cquote) * {pair.buy_spot.quantity}(buy_spot.quantity)')

                    if transaction.ttype == 'buy':
                        pair.profit = pair.value - pair.sell_spot.quantity

                        print(f'-> profit A: {pair.profit}(profit) = {pair.value}(value) - {pair.sell_spot.quantity}(sell_spot.quantity)')

                    elif transaction.ttype == 'sell':
                        pair.profit = pair.sell_spot.quantity - pair.value

                        print(f'-> profit B: {pair.profit}(profit) = {pair.sell_spot.quantity}(sell_spot.quantity) - {pair.value}(value)')

                elif pair.buy_spot.symbol == convert:
                    raise NotImplementedError()
                    if transaction.ttype == 'buy':
                        pair.value = cquote * pair.buy_spot.quantity
                        pair.profit = pair.sell_spot.quantity - pair.value

                    elif transaction.ttype == 'sell':
                        pair.value = cquote * pair.buy_spot.quantity
                        pair.profit = pair.value - pair.sell_spot.quantity

                else:
                    raise NotImplementedError()
                    x_quote = quotes.get(pair.sell_spot.symbol, pair.buy_spot.symbol)
                    sell_quote = quotes.get(convert, pair.sell_spot.symbol)
                    buy_quote = quotes.get(convert, pair.buy_spot.symbol)

                    print(f'-> x_quote: {x_quote}')
                    print(f'-> sell_quote: {sell_quote}')
                    print(f'-> buy_quote: {buy_quote}')

                    # sell_value = sell_quote * pair.sell_spot.quantity
                    # buy_value = buy_quote * pair.buy_spot.quantity
                    # pair.profit = buy_value - sell_value

                    # print(f'-> profit C: {pair.profit} = {buy_value}(buy_value) - {sell_value}(sell_value)')

                    # pair.value = buy_value

                transaction.profit = pair.profit

            else:
                spot = transaction.spot
                quote = quotes.get(convert, spot.symbol)
                spot.value = quote * spot.quantity
                spot.profit = spot.value
                spot.price = quote

                if transaction.ttype == 'in':
                    pass
                elif transaction.ttype == 'out':
                    spot.profit *= -1
                else:
                    raise ValueError(f'Unknown Transaction type: {transaction.ttype}')

                raise NotImplementedError('not pair')
                print(f'-> spot.profit: {spot.profit}')
                #transaction.profit = spot.profit
                #transaction.profit = 'not pair'

        # Holdings
        for hsym, holding in self.holdings.items():
            if holding.symbol == convert:
                self.costs = Spot(s=holding.symbol)
                self.costs.quantity = holding.quantity * -1
                continue

            quote = quotes.get(convert, holding.symbol)

            holding.quote = quote
            holding.value = quote * holding.quantity

            print('----------')
            holding.profit = 0.0
            for transaction in holding.transactions:
                profit = 0.0

                if transaction.ttype == 'buy':
                    if transaction.profit is not None:
                        profit = transaction.profit
                        print(f'-> transaction.profit: {transaction.profit}')

                elif transaction.ttype == 'sell':
                    print(f'-> pair: {transaction.pair}')

                    if pair.sell_spot.symbol == convert:
                        profit = -pair.sell_spot.quantity

                    elif pair.buy_spot.symbol == convert:
                        raise NotImplementedError('pair.buy_spot.symbol == convert')

                holding.profit += profit

                print(f'-> holding: hp={holding.profit} tt={transaction.ttype} profit={profit}')

        # Fees
        for fee_id, fee in self.fees.items():

            if fee.symbol == convert:
                self.fee_value += fee.quantity
            else:
                quote = quotes.get(convert, fee.symbol)
                self.fee_value += quote * fee.quantity
