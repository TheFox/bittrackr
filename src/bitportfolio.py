#!/usr/bin/env python3

import yaml
import signal
import shutil
import pandas as pd
from logging import getLogger, basicConfig
from typing import cast
from argparse import ArgumentParser, BooleanOptionalAction
from yaml import safe_load, dump as ydump
from json import loads, dumps
from cmc import get_quotes as cmc_get_quotes
from sty import fg, rs
from pathlib import Path
from portfolio import Portfolio
from transaction import Transaction
from apptypes import ConvertSymbols
from json_helper import ComplexEncoder
from quotes import Quotes
from helper import sort_holdings

_logger = getLogger(f'app.{__name__}')

class App():
    show_transactions: bool
    data_provider_id: str|None
    config: dict
    running: bool

    def __init__(self,
                 log_level: str = 'INFO',
                 base_dir: str|None = None,
                 config_path: str|None = None,
                 show_transactions: bool = False,
                 data_provider_id: str = 'cmc',
                 quotes_file: str|None = None,
                 change_dir: str|None = None,
                 max_depth: int|None = None,
                 filter_symbol: str|None = None,
                 filter_ttype: bool|None = None,
                 filter_open: bool|None = None,
                 load: bool|None = None,
                 save: bool|None = None,
                 ):

        logConfig = {
            'level': log_level,
            'format': '%(asctime)s %(process)d %(levelname)s %(name)s %(message)s',
        }
        basicConfig(**logConfig)

        self.terminal = shutil.get_terminal_size((80, 20))

        self.running = False
        self.show_transactions = show_transactions
        self.data_provider_id = data_provider_id

        if change_dir is None:
            self.change_dir = Path('.')
        else:
            self.change_dir = Path(change_dir)

        if base_dir is None:
            self.base_dir = self.change_dir / 'portfolios'
        else:
            self.base_dir = Path(base_dir)

        if config_path is None:
            self.config_path = self.change_dir / 'config.yml'
        else:
            self.config_path = Path(config_path)

        if quotes_file is None:
            self.quotes_file = None
        else:
            self.quotes_file = Path(quotes_file)

        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = safe_load(f)

        self.max_depth = max_depth
        self.filter_symbol = filter_symbol
        self.filter_ttype = filter_ttype
        self.load = load
        self.save = save
        self.filter_open = filter_open

        self.holding_minimum_amount = 0.0
        self.holding_minimum_ignore = []
        if 'holding_minimum' in self.config:
            holding_minimum = self.config['holding_minimum']
            self.holding_minimum_amount = holding_minimum['amount']
            self.holding_minimum_ignore = holding_minimum['ignore']

    def run(self):
        self.running = True

        portfolio = self._traverse(self.base_dir)
        portfolio.calc()

        psymbols = portfolio.get_convert_symbols(self.config['convert'])

        load_quotes = False
        if self.quotes_file is not None:
            if self.load:
                _logger.info(f'load quotes file: {self.quotes_file}')
                with open(self.quotes_file, 'r') as f:
                    quotes = Quotes(safe_load(f))
                    load_quotes = True

        if not load_quotes:
            quotes = self._get_quotes(psymbols, self.config['convert'])

        if self.quotes_file is not None:
            if self.save:
                _logger.info(f'save quotes file: {self.quotes_file}')
                with open(self.quotes_file, 'w') as f:
                    ydump(quotes.symbols, f, indent=2)

        portfolio.quotes(quotes, self.config['convert'])
        self._print_portfolio(portfolio)

    def shutdown(self, reason: str):
        print()
        print(f'-> shutting down: {reason}')

        self.running = False

    def _traverse(self, dir: Path, parent: Portfolio|None = None, level: int = 0) -> Portfolio:
        portfolio = Portfolio(name=dir.name, parent=parent)

        for file in dir.iterdir():
            if file.is_dir():
                nlevel = portfolio.level + 1
                sub_portfolio = self._traverse(file, portfolio, nlevel)
                portfolio.add_portfolio(sub_portfolio)

            elif file.is_file():
                raw_data = None
                with open(file, 'r') as f:
                    if str(file).endswith('.json'):
                        raw_data = loads(f.read())
                    if str(file).endswith('.yml'):
                        raw_data = yaml.safe_load(f)

                if 'ignore' in raw_data:
                    if raw_data['ignore']:
                        continue

                if 'sources' not in raw_data:
                    raise ValueError(f'No sources-field found in file: {file}')

                for source in raw_data['sources']:
                    if 'pairs' in source:
                        pairs = source['pairs']
                    if 'ignore' in source:
                        if source['ignore']:
                            continue

                    for pair in pairs:
                        if 'ignore' in pair and pair['ignore']:
                            continue

                        state = None
                        if 'state' in pair:
                            state = pair['state']

                        for transaction_j in pair['transactions']:
                            transaction_o = Transaction(
                                source=source['source'],
                                pair=pair['pair'],
                                d=transaction_j,
                            )

                            if transaction_o.ignore:
                                continue

                            if state is not None and transaction_o.state is None:
                                transaction_o.state = state

                            if transaction_o.state is None:
                                if transaction_o.ttype == 'buy':
                                    transaction_o.state = 'open'

                            add_trx = True

                            if self.filter_symbol is not None:
                                if transaction_o.sell_symbol != self.filter_symbol and transaction_o.buy_symbol != self.filter_symbol and (transaction_o.spot is not None and transaction_o.spot.symbol != self.filter_symbol or transaction_o.spot is None):
                                    add_trx = False

                            if self.filter_ttype is not None:
                                if transaction_o.ttype != self.filter_ttype:
                                    add_trx = False

                            if self.filter_open is not None:
                                if transaction_o.state != 'open':
                                    add_trx = False

                            if add_trx:
                                portfolio.add_transaction(transaction_o)

        return portfolio

    def _get_quotes(self, symbols: ConvertSymbols, convert: str) -> Quotes:
        _logger.debug('_get_quotes()')

        dp_config = self.config['data_provider']
        if dp_config['id'] == 'cmc':
            data_fetch_func = cmc_get_quotes
        else:
            raise ValueError(f'Unknown data provider: {dp_config["id"]}')

        quotes = Quotes()

        for convert, sym_list in symbols.items():
            _logger.debug(f'fetch data: {convert} start')
            data = data_fetch_func(
                api_host=dp_config['api']['host'],
                api_key=dp_config['api']['key'],
                convert=convert,
                symbols=sym_list,
            )
            _logger.debug(f'fetch data: {convert} done')

            for symbol in sym_list:
                _logger.debug(f'sym_list for {convert}: {symbol}')
                if symbol in data['data']:
                    sdata = data['data'].get(symbol)

                    if sdata is None or len(sdata) == 0:
                        print(f'----- data.data ({symbol}) -----')
                        print(dumps(data['data'], indent=2, cls=ComplexEncoder))
                        print('------------------------')

                        raise ValueError(f'sdata is empty: {symbol}')

                    try:
                        first = sdata[0]
                    except IndexError as error:
                        raise ValueError(f'sdata: {sdata}') from error

                    if convert in first['quote']:
                        quotes.add(convert, symbol, first['quote'][convert]['price'])

        return quotes

    def _print_portfolio(self, portfolio: Portfolio):
        self._print_portfolio_holdings(portfolio)
        self._print_portfolio_transactions(portfolio)
        self._print_subportfolios(portfolio)

    def _print_portfolio_holdings(self, portfolio: Portfolio):
        if portfolio.transactions_c == 0:
            return

        holdings = {
            'sym': [],
            'quant': [],
            'quote': [],
            'value': [],
            'profit': [], # accumulated profit
            'trx': [],
        }
        sorted_holdings = sorted(portfolio.holdings.items(), key=sort_holdings, reverse=True)
        total_value = 0.0
        for hsym, holding in sorted_holdings:
            if holding.symbol == self.config['convert']:
                continue

            if self.holding_minimum_amount is not None and holding.quantity < self.holding_minimum_amount:
                if holding.symbol not in self.holding_minimum_ignore:
                    continue

            holdings['sym'].append(holding.symbol)
            holdings['quant'].append(holding.quantity)
            holdings['quote'].append(holding.quote)
            holdings['value'].append(holding.value)
            holdings['profit'].append(holding.profit)
            holdings['trx'].append(holding.trx_count)

            total_value += holding.value

        if portfolio.costs is None:
            costs_q = 0.0
        else:
            costs_q = portfolio.costs.quantity  #+ portfolio.fee_value # TODO
        profit = total_value - costs_q

        print('-' * self.terminal.columns)
        print(f'Portfolio: {portfolio.name} (level={portfolio.level})')
        print(f'Transactions: {portfolio.transactions_c}')

        if costs_q >= 0.0:
            costs_color = fg.red
        else:
            costs_color = rs.all

        if profit >= 0:
            profit_color = rs.all
        else:
            profit_color = fg.red

        print(f'Fees:   {portfolio.fee_value:>10.2f} {self.config["convert"]}')
        if portfolio.costs is None:
            print(f'Costs:  {0:>10.2f} N/A')
        else:
            print(f'Costs:  {costs_color}{costs_q:>10.2f} {portfolio.costs.symbol}{rs.all}')
        print(f'Value:  {total_value:>10.2f} {self.config["convert"]}')
        print(f'Profit: {profit_color}{profit:>10.2f} {self.config["convert"]}{rs.all}')

        if len(holdings['sym']) == 0:
            return

        df = pd.DataFrame(data=holdings)

        df.rename(columns={'price': f'price({self.config["convert"]})'}, inplace=True)
        df.rename(columns={'quote': f'quote({self.config["convert"]})'}, inplace=True)
        df.rename(columns={'value': f'value({self.config["convert"]})'}, inplace=True)
        df.rename(columns={'profit': f'profit({self.config["convert"]})'}, inplace=True)

        df_s = df.to_string(index=False)
        print()
        print(df_s)

    def _print_portfolio_transactions(self, portfolio: Portfolio):
        if not self.show_transactions:
            return

        transactions = {
            'date': [],
            'type': [],
            'state': [],
            'pair': [],
            'quant': [],
            'price': [], # transaction price
            'quote': [], # current symbol price
            'profit': [],
            'sells': [],
            'sellq': [],
            'buys': [],
            'buyq': [],
            'accu': [],
            'source': [],
            'sellv': [],
            'buyv': [],
            'spotv': [],
            'target': [],
        }

        accumulated = 0.0
        show_target = False
        show_spotv = False

        sorted_transactions = sorted(portfolio.transactions, key=lambda t: t.date)
        sorted_transactions = cast(list[Transaction], sorted_transactions)
        for transaction in sorted_transactions:

            hide = False
            if transaction.ttype == 'buy':
                if transaction.state == 'closed':
                    hide = True
            elif transaction.ttype == 'sell':
                hide = True

            transactions['date'].append(transaction.date)
            transactions['type'].append(transaction.ttype)

            if transaction.state is None:
                transactions['state'].append('---')
            else:
                transactions['state'].append(transaction.state)

            if transaction.is_pair:
                transactions['pair'].append(transaction.pair.name)
                transactions['quant'].append(transaction.pair.buy_spot.quantity)
                transactions['price'].append(transaction.price)
                transactions['quote'].append(transaction.cprice)
                if hide:
                    transactions['profit'].append('---')
                    transactions['sellv'].append('---')
                    transactions['buyv'].append('---')
                else:
                    transactions['profit'].append(transaction.profit)
                    transactions['sellv'].append(transaction.pair.sell_spot.value)
                    transactions['buyv'].append(transaction.pair.buy_spot.value)
                transactions['spotv'].append('---')

                if transaction.target_spot is not None and transaction.target_spot.value is not None:
                    transactions['target'].append(transaction.target_spot.value)
                    show_target = True
                else:
                    transactions['target'].append('---')

                if transaction.ttype == 'buy':

                    if self.filter_symbol is not None:
                        if self.filter_symbol == transaction.pair.buy_spot.symbol:
                            accumulated += transaction.pair.buy_spot.quantity

                    transactions['sellq'].append(transaction.pair.sell_spot.quantity)
                    transactions['sells'].append(transaction.pair.sell_spot.symbol)
                    transactions['buyq'].append(transaction.pair.buy_spot.quantity)
                    transactions['buys'].append(transaction.pair.buy_spot.symbol)

                elif transaction.ttype == 'sell':

                    if self.filter_symbol is not None:
                        if self.filter_symbol == transaction.pair.buy_spot.symbol:
                            accumulated -= transaction.pair.buy_spot.quantity

                    transactions['sellq'].append(transaction.pair.buy_spot.quantity)
                    transactions['sells'].append(transaction.pair.buy_spot.symbol)
                    transactions['buyq'].append(transaction.pair.sell_spot.quantity)
                    transactions['buys'].append(transaction.pair.sell_spot.symbol)

                else:
                    raise ValueError(f'Unknown Transaction type: {transaction.ttype}')
            else:
                if transaction.ttype == 'in':
                    accumulated += transaction.spot.quantity
                elif transaction.ttype == 'out':
                    accumulated -= transaction.spot.quantity

                transactions['pair'].append(transaction.spot.symbol)
                transactions['quant'].append(transaction.spot.quantity)
                transactions['price'].append('---')
                #transactions['quote'].append(transaction.spot.price)
                transactions['quote'].append('???')
                transactions['profit'].append('---')
                transactions['sellq'].append('---')
                transactions['sells'].append('---')
                transactions['buyq'].append('---')
                transactions['buys'].append('---')
                transactions['sellv'].append('---')
                transactions['buyv'].append('---')
                transactions['spotv'].append(transaction.spot.value)
                transactions['target'].append('---')

                show_spotv = True

            transactions['accu'].append(accumulated)
            transactions['source'].append(transaction.source)

        if len(transactions['pair']) == 0:
            return

        try:
            df = pd.DataFrame(data=transactions)
        except ValueError as error:
            print('----- transactions -----')
            print(dumps(transactions, indent=2, cls=ComplexEncoder))
            print('------------------------')

            raise error

        df.style.format({
            'quote': '{:.2f}',
            'value': '{:.2f}',
            'profit': '{:.2f}',
        })

        df.rename(columns={'quote': f'quote({self.config["convert"]})'}, inplace=True)
        df.rename(columns={'profit': f'profit({self.config["convert"]})'}, inplace=True)
        df.rename(columns={'sellq': 'squant'}, inplace=True)
        df.rename(columns={'sells': 'ssym'}, inplace=True)
        df.rename(columns={'buyq': 'bquant'}, inplace=True)
        df.rename(columns={'buys': 'bsym'}, inplace=True)
        df.rename(columns={'sellv': f'sellv({self.config["convert"]})'}, inplace=True)
        df.rename(columns={'buyv': f'buyv({self.config["convert"]})'}, inplace=True)
        df.rename(columns={'spotv': f'spotv({self.config["convert"]})'}, inplace=True)

        df_cols = [
            'date',
            'type',
            'state',
            'pair',
            'quant',
            'price',
        ]
        if self.filter_symbol is None:
            df_cols += [f'quote({self.config["convert"]})']
        df_cols += [
            f'profit({self.config["convert"]})',
            f'sellv({self.config["convert"]})',
            f'buyv({self.config["convert"]})',
        ]
        if show_spotv:
            df_cols += [f'spotv({self.config["convert"]})']
        df_cols += [
            'ssym',
            'squant',
            'bsym',
            'bquant',
        ]

        if self.filter_symbol is not None:
            df_cols.append('accu')

        if show_target:
            df_cols.append('target')
        df_cols.append('source')

        df_s = df.to_string(index=False, columns=df_cols)
        print()
        print(df_s)

    def _print_subportfolios(self, portfolio: Portfolio):
        nlevel = portfolio.level + 1
        if self.max_depth is not None and nlevel > self.max_depth:
            print(f'-> max depth reached: {nlevel}')
            return

        subs = sorted(portfolio.subs, key=lambda p: p.name)
        for sub_portfolio in subs:
            self._print_portfolio(sub_portfolio)

def main():
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)

    parser = ArgumentParser(prog='bitportfolio', description='BitPortfolio')
    parser.add_argument('-X', '--log-level', type=str, nargs='?', required=False, help='Log Level', default='WARN')
    parser.add_argument('-C', '--chdir', type=str, nargs='?', required=False, help='Change directory and look for files')
    parser.add_argument('-c', '--config', type=str, nargs='?', required=False, help='Path to Config File')
    parser.add_argument('-d', '--basedir', type=str, nargs='?', required=False, help='Path to directory')
    parser.add_argument('-p', '--dataprovider', type=str, nargs='?', required=False, help='ID', default='cmc')
    parser.add_argument('-t', '--transactions', action=BooleanOptionalAction, help='Show transactions', default=False)
    parser.add_argument('-q', '--quotes-file', type=str, nargs='?', required=False, help='Save/load quotes from file')
    parser.add_argument('-m', '--max-depth', type=int, nargs='?', required=False, help='Max directory depth')
    parser.add_argument('-s', '--symbol', type=str, nargs='?', required=False, help='Handle only Transactions with given symbol')
    parser.add_argument('-b', '--buy', action=BooleanOptionalAction, help='Show only buy Transactions')
    parser.add_argument('-s', '--sell', action=BooleanOptionalAction, help='Show only sell Transactions')
    parser.add_argument('-o', '--open', action=BooleanOptionalAction, help='Show only open Transactions')
    parser.add_argument('-l', '--load', action=BooleanOptionalAction, help='Load Quotes file')
    parser.add_argument('--save', action=BooleanOptionalAction, help='Save Quotes file')

    args = parser.parse_args()
    # print(args)

    filter_ttype = None
    if args.buy:
        filter_ttype = 'buy'
    elif args.sell:
        filter_ttype = 'sell'

    app = App(
        log_level=args.log_level,
        base_dir=args.basedir,
        config_path=args.config,
        show_transactions=args.transactions,
        data_provider_id=args.dataprovider,
        quotes_file=args.quotes_file,
        change_dir=args.chdir,
        max_depth=args.max_depth,
        filter_symbol=args.symbol,
        filter_ttype=filter_ttype,
        filter_open=args.open,
        load=args.load,
        save=args.save,
    )

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
