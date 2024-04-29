#!/usr/bin/env python3

import signal
import argparse
from json import loads
from cmc import get_quotes as cmc_get_quotes
from sty import fg, bg, ef, rs
from datetime import datetime
from pathlib import Path

class App():
    config: dict
    running: bool

    def __init__(self, config_path: str|None):
        print(f'-> config path: {config_path}')

        if config_path is not None:
            with open(config_path, 'r') as f:
                self.config = loads(f.read())

    def run(self, basedir: str):
        self.running = True

        print(f'-> basedir: {basedir}')
        data = self._traverse(Path(basedir))

        print(f'-> data: {data}')

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
                print(f'data: {data}')

                for pair_id, pdata in data['pairs'].items():
                    if pair_id not in collection['pairs']:
                        collection['pairs'][pair_id] = {
                            'transactions': [],
                            'prices': [],
                            'quantity': 0,
                            'fee': 0,
                            'locations': [],
                        }

                    collection['pairs'][pair_id]['transactions'].extend(data['transactions'])

                    collection['pairs'][pair_id]['prices'].extend(data['prices'])

                    collection['pairs'][pair_id]['quantity'] += data['quantity']
                    collection['pairs'][pair_id]['fee'] += data['fee']

                    collection['pairs'][pair_id]['locations'].extend(data['locations'])

            else:
                print(f'-> f: {file}')
                with open(file, 'r') as f:
                    json = loads(f.read())

                if json['pair'] not in collection['pairs']:
                    collection['pairs'][json['pair']] = {
                        'transactions': [],
                        'prices': [],
                        'quantity': 0,
                        'fee': 0,
                        'locations': [],
                    }

                for transaction in json['transactions']:
                    collection['pairs'][json['pair']]['transactions'].append(transaction)

                    if transaction['type'] == 'buy':
                        collection['pairs'][json['pair']]['quantity'] += transaction['quantity']
                    elif transaction['type'] == 'sell':
                        collection['pairs'][json['pair']]['quantity'] -= transaction['quantity']

        return collection

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
