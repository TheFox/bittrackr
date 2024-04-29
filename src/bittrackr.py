#!/usr/bin/env python3

import signal
import argparse
import shutil
from json import loads
from time import sleep
from cmc import get_quotes as cmc_get_quotes
from sty import fg, bg, ef, rs
from datetime import datetime

CLEAR_SCREEN='\033[2J'
JUMP_BEGINNING='\033[1;1H'

class App():
    config: dict
    _max_updates: int
    running: bool
    data: dict
    screen: dict

    def __init__(self, config_path: str|None, update_interval: int|None = None, max_updates: int|None = None):
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

        if update_interval is not None:
            self.config['update_interval'] = update_interval

        self._max_updates = max_updates

        self.data = {}
        for sym in self.config['symbols']:
            self.data[sym] = {
                'symbol': sym,
                'direction': 0,
                'prev_price': None,
                'prev_volume_24h': None,
                'diff_volume_24h': 0.0,
                'dp': {
                    'quote_price': None,
                    'last_updated': None,
                    'volume_24h': None,
                    'volume_change_24h': None,
                    'percent_change_24h': None,
                },
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

        cycle_n = 0
        while self.running:
            cycle_n += 1

            self._data_update()
            self._screen_update()

            if self._max_updates is not None and cycle_n >= self._max_updates:
                self.shutdown('max cycles reached')
                break

            print(f'update_interval={self.config["update_interval"]} cycle={cycle_n} mu={self._max_updates}')
            for n in sleep_list:
                print(f'  next update in {n}    \r', end='', flush=True)
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

                    self.data[sym]['dp']['quote_price'] = fiat_quote['price']
                    self.data[sym]['dp']['last_updated'] = fiat_quote['last_updated']
                    self.data[sym]['dp']['volume_24h'] = fiat_quote['volume_24h']
                    self.data[sym]['dp']['volume_change_24h'] = fiat_quote['volume_change_24h']
                    self.data[sym]['dp']['percent_change_24h'] = fiat_quote['percent_change_24h']

                    if self.data[sym]['prev_price'] is not None:
                        if self.data[sym]['dp']['quote_price'] > self.data[sym]['prev_price']:
                            self.data[sym]['direction'] = 1
                        elif self.data[sym]['dp']['quote_price'] < self.data[sym]['prev_price']:
                            self.data[sym]['direction'] = -1
                        else:
                            self.data[sym]['direction'] = 0

                    if self.data[sym]['prev_volume_24h'] is not None:
                        self.data[sym]['diff_volume_24h'] = self.data[sym]['dp']['volume_24h'] - self.data[sym]['prev_volume_24h']
                    self.data[sym]['prev_volume_24h'] = self.data[sym]['dp']['volume_24h']

                    self.data[sym]['prev_price'] = self.data[sym]['dp']['quote_price']
            else:
                raise ValueError(f'Unknown data provider: {dp["id"]}')

    def _screen_update(self):
        # Jump to top left.
        print(JUMP_BEGINNING, end='', flush=True)

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'Last update: {now}')
        print()
        print('SYM     PRICE     24P%     24V%              24V           24V/LU')
        print('-----------------------------------------------------------------')

        row_width = 0
        row_c = 0
        column_c = 0
        column_base = 1
        for sym, coin in self.data.items():
            row_c += 1

            out_r = '{:4s} {:>8.2f}{} {:>8.2f} {:>8.2f} {:>16.2f} {:>16.2f}'.format(
                sym,
                coin['dp']['quote_price'],
                rs.all,
                coin['dp']['percent_change_24h'],
                coin['dp']['volume_change_24h'],
                coin['dp']['volume_24h'],
                coin['diff_volume_24h'],
            )
            row_width = max(row_width, len(out_r) - 3)

            if coin['direction'] == 1:
                fg_color = fg.green
            elif coin['direction'] == -1:
                fg_color = fg.red
            else:
                fg_color = fg.black

            row_s = fg_color + out_r
            print(row_s, end='', flush=True)
            sleep(0.1)
            print(f'\033[{column_base}G', end='', flush=True)
            sleep(0.05)
            print('\033[1B', end='', flush=True)
            sleep(0.1)

            if row_c == self.screen['lines']:
                column_c += 1
                column_base += row_width + 3

                print(f'\033[1;{column_base}H', end='', flush=True)
                sleep(0.1)

            if not self.running:
                break

        print('\033[1E', end='', flush=True)


    def shutdown(self, reason: str):
        print()
        print(f'-> shutting down: {reason}')
        self.running = False

    def _default_config(self):
        return {
            'update_interval': 60,
            'convert': 'USD',
            'symbols': ['BTC'],
            'data_providers': [],
        }

def main():
    parser = argparse.ArgumentParser(prog='bittrackr', description='BitTrackr')
    parser.add_argument('-c', '--config', type=str, nargs=1, required=False, help='Path to Config File', default=[None])
    parser.add_argument('-i', '--update-interval', type=int, nargs=1, required=False, help='Overwrite update_interval in config', default=[300])
    parser.add_argument('-u', '--max-updates', type=int, nargs=1, required=False, help='Max Updates', default=[None])

    args = parser.parse_args()
    print(args)

    app = App(
        args.config[0],
        update_interval=args.update_interval[0],
        max_updates=args.max_updates[0],
    )

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
