#!/usr/bin/env python3

import signal
import argparse
import shutil
import os
from json import loads
from time import sleep
from cmc import get_quotes as cmc_get_quotes
from sty import fg, bg, ef, rs

CLEAR_SCREEN='\033[2J'
JUMP_BEGINNING='\033[1;1H'

def _m(i: int) -> str:
    if i == 1:
        return '^'
    if i == -1:
        return 'v'
    return '-'

class App():
    config: dict
    running: bool
    data: dict
    screen: dict

    def __init__(self, config_path: str|None):
        print(f'-> config path: {config_path}')
        if config_path is None:
            self.config = self._default_config()
        else:
            with open(config_path, 'r') as f:
                config = loads(f.read())

            dc = self._default_config()
            self.config = {
                **dc,
                **config,
            }

        self.data = {}
        for sym in self.config['symbols']:
            self.data[sym] = {
                'symbol': sym,
                'last_updated': None,
                'quote_price': None,
                'prev_price': None,
                'direction': 0,
                'history': ['-'] * self.config['history_length'],
            }

        terminal = shutil.get_terminal_size((80, 20))
        self.screen = {
            'lines': terminal.lines,
            'columns': terminal.columns,
        }
        # self.screen['lines'] = 3

    def run(self):
        self.running = True

        sleep_list = list(reversed(list(range(1, self.config['update_interval']))))

        # Clear screen
        print(CLEAR_SCREEN, end='', flush=True)

        # Jump to top left.
        print(JUMP_BEGINNING, end='', flush=True)

        while self.running:
            self._data_update()
            self._screen_update()

            for n in sleep_list:
                print(f'  next update in {n} ({self.config["update_interval"]})    \r', end='', flush=True)
                sleep(1)
                if not self.running:
                    break
            print('\033[2K', end='', flush=True)

    def _data_update(self):
        for dp in self.config['data_providers']:
            if dp['id'] == 'cmc':
                response = cmc_get_quotes(
                    api_host=dp['api']['host'],
                    api_key=dp['api']['key'],
                    convert=self.config['convert'],
                    symbols=self.config['symbols'],
                )
                for sym, sdata in response['data'].items():
                    fsdata = sdata[0]
                    fiat_quote = fsdata['quote'][self.config['convert']]

                    self.data[sym]['quote_price'] = fiat_quote['price']
                    self.data[sym]['last_updated'] = fiat_quote['last_updated']

                    if self.data[sym]['prev_price'] != None:
                        if self.data[sym]['quote_price'] > self.data[sym]['prev_price']:
                            self.data[sym]['direction'] = 1
                        elif self.data[sym]['quote_price'] < self.data[sym]['prev_price']:
                            self.data[sym]['direction'] = -1
                        else:
                            self.data[sym]['direction'] = 0

                        if len(self.data[sym]['history']) >= self.config['history_length']:
                            self.data[sym]['history'].pop(0)
                        self.data[sym]['history'].append(self.data[sym]['direction'])

                    self.data[sym]['prev_price'] = self.data[sym]['quote_price']
            else:
                raise ValueError(f'Unknown data provider: {dp["id"]}')

    def _screen_update(self):
        # print('-> _screen_update()')

        # Jump to top left.
        print(JUMP_BEGINNING, end='', flush=True)

        row_width = 0
        row_c = 0
        column_c = 0
        column_base = 1
        for sym, coin in self.data.items():
            row_c += 1

            history = ''.join(list(map(_m, coin['history'])))
            out = '{:4s} {:>8.2f} {}'.format(sym, coin['quote_price'], history)
            row_width = max(row_width, len(out))

            if coin['direction'] == 1:
                fg_color = fg.green
            elif coin['direction'] == -1:
                fg_color = fg.red
            else:
                fg_color = fg.black

            row_s = fg_color + out + rs.all
            print(row_s, end='', flush=True)
            sleep(0.1)
            print(f'\033[{column_base}G', end='', flush=True)
            sleep(0.1)
            print('\033[1B', end='', flush=True)
            sleep(0.1)

            if row_c == self.screen['lines']:
                column_c += 1
                column_base += row_width + 3

                print(f'\033[1;{column_base}H', end='', flush=True)
                sleep(0.1)

            if not self.running:
                break

        print(f'\033[1E', end='', flush=True)

    def shutdown(self, reason: str):
        print()
        print(f'-> shutting down: {reason}')
        self.running = False

    def _default_config(self):
        return {
            'update_interval': 60,
            'history_length': 5,
            'convert': 'USD',
            'symbols': ['BTC'],
            'data_providers': [],
        }

def main():
    parser = argparse.ArgumentParser(prog='bittrackr', description='BitTrackr')
    parser.add_argument('-c', '--config', type=str, nargs=1, required=False, help='Path to Config File', default=[None])

    args = parser.parse_args()
    print(args)

    app = App(args.config[0])

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
