#!/usr/bin/env python3

import signal
import argparse
from json import loads, dumps
from cmc import get_quotes as cmc_get_quotes
from sty import fg, bg, ef, rs
from datetime import datetime
from pathlib import Path

class App():
    config: dict
    running: bool

    def __init__(self, config_path: str|None):
        print(f'-> config path: {config_path}')

        if config_path is None:
            raise Exception('Config file not provided')

        with open(config_path, 'r') as f:
            self.config = loads(f.read())

    def run(self, basedir: str):
        self.running = True

        print(f'-> basedir: {basedir}')
        data = self._traverse(Path(basedir))

        unique_symbols = set()
        for pair_id, pdata in data['pairs'].items():
            unique_symbols.add(pdata['sell_symbol'])
            unique_symbols.add(pdata['buy_symbol'])
        self.quotes = self._get_quotes(unique_symbols)

        self._print_data(data)

    def shutdown(self, reason: str):
        print()
        print(f'-> shutting down: {reason}')
        self.running = False

    def _traverse(self, dir: Path, level: int = 0) -> dict:
        print(f'-> dir: {dir.name}')
        collection = {
            'dir': dir.name,
            'pairs': {},
        }
        for file in dir.iterdir():
            if file.is_dir():
                data = self._traverse(file, level + 1)

                for pair_id, pdata in data['pairs'].items():
                    if pair_id not in collection['pairs']:
                        collection['pairs'][pair_id] = {
                            'sell_symbol': pdata['sell_symbol'],
                            'buy_symbol': pdata['buy_symbol'],
                            'symbols': [],
                            'transactions': [],
                            'prices': [],
                            'quantity': 0.0,
                            'fees': 0.0,
                            'locations': [],
                        }

                    collection['pairs'][pair_id]['symbols'].extend(pdata['symbols'])
                    collection['pairs'][pair_id]['transactions'].extend(pdata['transactions'])

                    collection['pairs'][pair_id]['prices'].extend(pdata['prices'])

                    collection['pairs'][pair_id]['quantity'] += pdata['quantity']
                    collection['pairs'][pair_id]['fees'] += pdata['fees']

                    collection['pairs'][pair_id]['locations'].extend(pdata['locations'])

            else:
                print(f'-> f: {file}')
                with open(file, 'r') as f:
                    json = loads(f.read())

                pair = json['pair']
                sell_symbol, buy_symbol = pair.split('/')

                if pair not in collection['pairs']:
                    collection['pairs'][pair] = {
                        'sell_symbol': sell_symbol,
                        'buy_symbol': buy_symbol,
                        'symbols': [],
                        'transactions': [],
                        'prices': [],
                        'quantity': 0.0,
                        'fees': 0.0,
                        'locations': [],
                    }

                collection['pairs'][pair]['symbols'].append(sell_symbol)
                collection['pairs'][pair]['symbols'].append(buy_symbol)

                for transaction in json['transactions']:
                    collection['pairs'][pair]['transactions'].append(transaction)

                    if transaction['type'] == 'buy':
                        collection['pairs'][pair]['quantity'] += transaction['quantity']
                    elif transaction['type'] == 'sell':
                        collection['pairs'][pair]['quantity'] -= transaction['quantity']

                    collection['pairs'][pair]['fees'] += transaction['fee']
                    collection['pairs'][pair]['locations'].append(transaction['location'])

        return collection

    def _get_quotes(self, symbols: list) -> dict:
        print('-> get_quotes')
        cmc_config = self.config['data_providers'][0]
        return cmc_get_quotes(
            api_host=cmc_config['api']['host'],
            api_key=cmc_config['api']['key'],
            convert=self.config['convert'],
            symbols=symbols,
        )

    def _print_data(self, data: dict):
        print('------------')
        print(dumps(self.quotes, indent=4))
        print('------------')
        print(dumps(data, indent=4))
        print('------------')

        for pair_id, pdata in data['pairs'].items():
            coin = self.quotes['data'][pdata['buy_symbol']]
            print(f'-> pair: {pair_id}')
            # print(f'-> symbols: {pdata["symbols"]}')
            print(f'-> transactions: {len(pdata["transactions"])}')
            print(f'-> quantity: {pdata["quantity"]}')
            print(f'-> fees: {pdata["fees"]}')
            # print(f'-> locations: {pdata["locations"]}')
            print()

def main():
    parser = argparse.ArgumentParser(prog='bitportfolio', description='BitPortfolio')
    parser.add_argument('-c', '--config', type=str, nargs=1, required=False, help='Path to Config File', default=[None])
    parser.add_argument('-d', '--basedir', type=str, nargs=1, required=False, help='Path to directory', default=[None])

    args = parser.parse_args()
    print(args)

    app = App(args.config[0])

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run(args.basedir[0])
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
