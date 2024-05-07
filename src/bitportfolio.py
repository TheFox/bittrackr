#!/usr/bin/env python3

import sys
import signal
import shutil
import pandas as pd

from argparse import ArgumentParser, BooleanOptionalAction
from json import loads, load, dumps, dump
from cmc import get_quotes as cmc_get_quotes
from sty import fg, bg, ef, rs
from pathlib import Path
from portfolio import Portfolio
from transaction import Transaction
from spot import Spot
from apptypes import Quotes
from json_helper import ComplexEncoder
from portfolio import Holding

def _sort_holdings(item: tuple[str, Holding]):
    # print(f'-> sort: {item}')
    value = item[1].value
    if value is None:
        return 0.0
    return value

class App():
    show_transactions: bool
    data_provider_id: str|None
    config: dict
    running: bool

    def __init__(self, base_dir: str|None = None, config_path: str|None = None, show_transactions: bool = False, data_provider_id: str = 'cmc', quotes_file: str|None = None, change_dir: str|None = None, max_depth: int|None = None):
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
            self.config_path = self.change_dir / 'config.json'
        else:
            self.config_path = Path(config_path)

        if quotes_file is None:
            self.quotes_file = None
        else:
            self.quotes_file = Path(quotes_file)

        # print(f'-> change_dir: {self.change_dir}')
        # print(f'-> base_dir: {self.base_dir}')
        # print(f'-> config_path: {self.config_path}')
        # print(f'-> quotes_file: {self.quotes_file}')

        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = loads(f.read())

        self.max_depth = max_depth

    def run(self):
        self.running = True

        portfolio = self._traverse(self.base_dir)
        portfolio.calc()

        # print('------- portfolio -------')
        # print(dumps(portfolio, indent=2, cls=ComplexEncoder))
        # print('------------------------')

        quotes = self._get_quotes()
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
                nlevel = level + 1
                if self.max_depth is not None and nlevel >= self.max_depth:
                    continue

                sub_portfolio = self._traverse(file, portfolio, nlevel)
                portfolio.add_portfolio(sub_portfolio)

            elif file.is_file():
                if not str(file).endswith('.json'):
                    continue

                with open(file, 'r') as f:
                    json = loads(f.read())

                for pair in json:
                    for transaction_j in pair['transactions']:
                        transaction_o = Transaction(pair=pair['pair'], d=transaction_j)

                        portfolio.add_transaction(transaction_o)

        return portfolio

    def _get_quotes(self) -> Quotes:
        symbols = None
        if 'portfolio' in self.config:
            if 'symbols' in self.config['portfolio']:
                symbols = self.config['portfolio']['symbols']
        if symbols is None:
            symbols = self.config['symbols']

        config = None
        for dp_config in self.config['data_providers']:
            if dp_config['enabled']:
                if self.data_provider_id is None:
                    # Take first.
                    config = dp_config
                else:
                    # Compare ID.
                    if self.data_provider_id == dp_config['id']:
                        config = dp_config
                        break

        data = None
        if config is not None:
            f = getattr(sys.modules[__name__], f'{config["id"]}_get_quotes')
            data = f(
                api_host=config['api']['host'],
                api_key=config['api']['key'],
                convert=self.config['convert'],
                symbols=symbols,
            )

            # print('----------- data -----------')
            # print(dumps(data, indent=2))
            # print('----------------------------')

        convert = self.config['convert']

        load_quotes = False
        symbol_values: Quotes = {}
        if data is None:
            if self.quotes_file is not None and self.quotes_file.exists():
                with open(self.quotes_file, 'r') as f:
                    symbol_values = load(f)
                load_quotes = True
        else:
            for symbol in symbols:
                if symbol in data['data']:
                    sdata = data['data'][symbol]
                    first_q = sdata[0]
                    if convert in first_q['quote']:
                        symbol_values[symbol] = first_q['quote'][convert]['price']

        # print(f'----- symbol_values ({load_quotes}) -----')
        # print(dumps(symbol_values, indent=2))
        # print('----------------------------')

        if not load_quotes and self.quotes_file is not None:
            with open(self.quotes_file, 'w') as f:
                dump(symbol_values, f, indent=2)

        return symbol_values

    def _print_portfolio(self, portfolio: Portfolio):
        sell_symbols = ', '.join(list(portfolio.sell_symbols))
        buy_symbols = ', '.join(list(portfolio.buy_symbols))

        cost_spot = Spot(s=self.config['convert'])
        holdings = {
            'sym': [],
            'quote': [],
            'holding': [],
            'value': [],
            'trx': [],
        }
        sorted_holdings = sorted(portfolio.holdings.items(), key=_sort_holdings, reverse=True)
        total_value = 0.0
        for sym, spot in sorted_holdings:
            if spot.quantity == 0.0:
                continue

            if spot.symbol == self.config['convert']:
                # cost_spot.quantity = spot.quantity
                cost_spot.quantity = spot.quantity * -1
            else:
                holdings['sym'].append(spot.symbol)
                holdings['quote'].append(spot.quote)
                holdings['holding'].append(spot.quantity)
                holdings['value'].append(spot.value)
                holdings['trx'].append(len(spot.transactions))

            total_value += spot.value
        profit = total_value - cost_spot.quantity

        print()
        print('-' * self.terminal.columns)
        print(f'Portfolio: {portfolio.name} (level={portfolio.level})')
        print(f'Transactions: {portfolio.transactions_c}')

        if sell_symbols != '':
            print(f'Sell symbols: {sell_symbols}')
        if buy_symbols != '':
            print(f'Buy  symbols: {buy_symbols}')

        if cost_spot.quantity >= 0:
            costs_color = fg.red
        else:
            costs_color = fg.black

        if profit >= 0:
            profit_color = fg.black
        else:
            profit_color = fg.red

        print(f'Fees:   {portfolio.fee_value:>8.2f} {self.config["convert"]}')
        print(f'Costs:  {costs_color}{cost_spot.quantity:>8.2f} {cost_spot.symbol}{rs.all}')
        print(f'Value:  {total_value:>8.2f} {self.config["convert"]}')
        print(f'Profit: {profit_color}{profit:>8.2f} {self.config["convert"]}{rs.all}')

        if len(holdings['sym']) > 0:
            df = pd.DataFrame(data=holdings)
            df['quote'] = df['quote'].apply(lambda x: '{:.6f}'.format(x))
            df['holding'] = df['holding'].apply(lambda x: '{:.5f}'.format(x))
            df['value'] = df['value'].apply(lambda x: '{:.2f}'.format(x))

            df.rename(columns={'quote': f'quote({self.config["convert"]})'}, inplace=True)
            df.rename(columns={'value': f'value({self.config["convert"]})'}, inplace=True)

            df_s = df.to_string(index=False)
            print()
            print(df_s)

        subs = sorted(portfolio.subs, key=lambda p: p.name)
        for sub_portfolio in subs:
            self._print_portfolio(sub_portfolio)

def main():
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    #pd.options.display.float_format = '{:,.2f}'.format

    parser = ArgumentParser(prog='bitportfolio', description='BitPortfolio')
    parser.add_argument('-c', '--config', type=str, nargs='?', required=False, help='Path to Config File')
    parser.add_argument('-d', '--basedir', type=str, nargs='?', required=False, help='Path to directory')
    parser.add_argument('-p', '--dataprovider', type=str, nargs='?', required=False, help='ID', default='cmc')
    parser.add_argument('-t', '--transactions', action=BooleanOptionalAction, help='Show transactions', default=False)
    parser.add_argument('-qf', '--quotes-file', type=str, nargs='?', required=False, help='Save/load quotes from file')
    parser.add_argument('-C', '--changedir', type=str, nargs='?', required=False, help='Change directory and look for files')
    parser.add_argument('-l', '--max-depth', type=int, nargs='?', required=False, help='Max directory depth')

    args = parser.parse_args()
    print(args)

    app = App(
        base_dir=args.basedir,
        config_path=args.config,
        show_transactions=args.transactions,
        data_provider_id=args.dataprovider,
        quotes_file=args.quotes_file,
        change_dir=args.changedir,
        max_depth=args.max_depth,
    )

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
