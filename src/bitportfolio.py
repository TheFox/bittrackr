#!/usr/bin/env python3

import signal
from argparse import ArgumentParser, BooleanOptionalAction
from json import loads, dumps
from cmc import get_quotes as cmc_get_quotes
from sty import fg, bg, ef, rs
from datetime import datetime
from pathlib import Path

class App():
    config: dict
    running: bool
    quotes: dict

    def __init__(self, config_path: str|None):
        print(f'-> config path: {config_path}')

        self.quotes = {}

        if config_path is None:
            raise Exception('Config file not provided')

        with open(config_path, 'r') as f:
            self.config = loads(f.read())

    def run(self, basedir: str, show_transactions: bool = False):
        self.running = True

        print(f'-> basedir: {basedir}')
        data = self._traverse(Path(basedir))
        data = self._prepare(data)

        symbols = data['buy_symbols']
        print(f'-> symbols: {symbols}')
        self.quotes = self._get_quotes(symbols)
        data = self._calc_value(data)

        self._print_data(data)

    def shutdown(self, reason: str):
        print()
        print(f'-> shutting down: {reason}')
        self.running = False

    def _traverse(self, dir: Path, level: int = 0) -> dict:
        print(f'-> dir: {dir.name}')
        collection = {
            'symbols': [],
            'sell_symbols': [],
            'buy_symbols': [],
            'fees': 0.0,
            'value': 0.0,
            'locations': [],
            'pairs': {},
        }
        for file in dir.iterdir():
            if file.is_dir():
                data = self._traverse(file, level + 1)

                collection['symbols'].extend(data['symbols'])
                collection['sell_symbols'].extend(data['sell_symbols'])
                collection['buy_symbols'].extend(data['buy_symbols'])
                collection['value'] += (data['value'])

                for pair_id, pdata in data['pairs'].items():
                    if pair_id not in collection['pairs']:
                        collection['pairs'][pair_id] = {
                            'sell_symbol': pdata['sell_symbol'],
                            'buy_symbol': pdata['buy_symbol'],
                            'quantity': 0.0,
                            'fees': 0.0,
                            'value': 0.0,
                            'locations': [],
                            'transactions': [],
                        }

                    collection['fees'] += pdata['fees']
                    collection['locations'].extend(pdata['locations'])

                    collection['pairs'][pair_id]['transactions'].extend(pdata['transactions'])
                    collection['pairs'][pair_id]['quantity'] += pdata['quantity']
                    collection['pairs'][pair_id]['fees'] += pdata['fees']
                    collection['pairs'][pair_id]['locations'].extend(pdata['locations'])

            else:
                if not str(file).endswith('.json'):
                    continue

                print(f'-> f: {file}')
                with open(file, 'r') as f:
                    json = loads(f.read())

                pair = json['pair']
                sell_symbol, buy_symbol = pair.split('/')

                if pair not in collection['pairs']:
                    collection['pairs'][pair] = {
                        'sell_symbol': sell_symbol,
                        'buy_symbol': buy_symbol,
                        'quantity': 0.0,
                        'fees': 0.0,
                        'value': 0.0,
                        'locations': [],
                        'transactions': [],
                    }

                collection['symbols'].append(sell_symbol)
                collection['symbols'].append(buy_symbol)
                collection['sell_symbols'].append(sell_symbol)
                collection['buy_symbols'].append(buy_symbol)

                for transaction in json['transactions']:
                    # print('---------- transaction ----------')
                    # print(transaction)
                    # print('---------------------------------')

                    transaction['cost'] = transaction['price'] * transaction['quantity']

                    collection['fees'] += transaction['fee']

                    collection['pairs'][pair]['transactions'].append(transaction)

                    if transaction['type'] == 'buy':
                        collection['pairs'][pair]['quantity'] += transaction['quantity']
                    elif transaction['type'] == 'sell':
                        collection['pairs'][pair]['quantity'] -= transaction['quantity']

                    collection['pairs'][pair]['fees'] += transaction['fee']

                    location = transaction.get('location')
                    if location is not None:
                        collection['pairs'][pair]['locations'].append(transaction['location'])
                        collection['locations'].append(transaction['location'])

        return collection

    def _prepare(self, data: dict) -> dict:
        print('-> _prepare')

        symbols = set()
        for sym in data['symbols']:
            symbols.add(sym)
        data['symbols'] = list(symbols)

        sell_symbols = set()
        for sym in data['sell_symbols']:
            sell_symbols.add(sym)
        data['sell_symbols'] = list(sell_symbols)

        buy_symbols = set()
        for sym in data['buy_symbols']:
            buy_symbols.add(sym)
        data['buy_symbols'] = list(buy_symbols)

        locations = set()
        for sym in data['locations']:
            locations.add(sym)
        data['locations'] = list(locations)

        for pid, pdata in data['pairs'].items():
            locations = set()
            for sym in pdata['locations']:
                locations.add(sym)
            data['pairs'][pid]['locations'] = list(locations)

            transactions = sorted(pdata['transactions'], key=lambda t: t['date'])
            data['pairs'][pid]['transactions'] = transactions

        return data

    def _get_quotes(self, symbols: list) -> dict:
        print(f'-> _get_quotes({symbols})')
        cmc_config = self.config['data_providers'][0]
        data = cmc_get_quotes(
            api_host=cmc_config['api']['host'],
            api_key=cmc_config['api']['key'],
            convert=self.config['convert'],
            symbols=symbols,
        )
        # print('----------- data -----------')
        # print(dumps(data, indent=2))
        # print('----------------------------')
        return data

    def _calc_value(self, data: dict):
        print('-> _calc_value')

        for pid, pdata in data['pairs'].items():
            quote = self.quotes['data'][pdata["buy_symbol"]][0]['quote'][self.config['convert']]['price']
            data['pairs'][pid]['quote'] = quote

            value = quote * pdata['quantity']
            data['pairs'][pid]['value'] = value

            transactions = []
            for transaction in pdata['transactions']:
                transaction['value'] = quote * transaction['quantity']
                transactions.append(transaction)

            data['pairs'][pid]['transactions'] = transactions

        return data

    def _print_data(self, data: dict):
        print('------------')
        print('SYM QUANTITY VALUE COST PROFIT')

        for pair_id, pdata in data['pairs'].items():
            print(dumps(pdata, indent=2))
            # print(f'-> pair: {pair_id}')
            # print(f'-> transactions: {len(pdata["transactions"])}')
            # print(f'-> quantity: {pdata["quantity"]}')
            # print(f'-> fees: {pdata["fees"]}')
            # print(f'-> locations: {pdata["locations"]}')
            # print(f'-> value: {pdata["value"]}')
            row = '{} {}  {:.2f}'.format(
                pdata['buy_symbol'],
                pdata['quantity'],
                pdata['value'],
            )
            print(row)

def main():
    parser = ArgumentParser(prog='bitportfolio', description='BitPortfolio')
    parser.add_argument('-c', '--config', type=str, nargs=1, required=False, help='Path to Config File', default=[None])
    parser.add_argument('-d', '--basedir', type=str, nargs=1, required=False, help='Path to directory', default=[None])
    parser.add_argument('-t', '--transactions', action=BooleanOptionalAction, help='Show transactions', default=False)

    args = parser.parse_args()
    print(args)

    app = App(args.config[0])

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run(args.basedir[0], args.transactions)
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
