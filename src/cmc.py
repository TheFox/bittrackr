
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json

def get_quotes(api_host: str = 'sandbox-api.coinmarketcap.com', api_key: str = 'b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c', convert: str = 'USD', symbols: list = ['BTC', 'ETH']):
    symbol_s = ','.join(symbols)
    url = f'https://{api_host}/v2/cryptocurrency/quotes/latest'
    parameters = {
        'convert': convert,
        'symbol': symbol_s,
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }

    session = Session()
    session.headers.update(headers)

    try:
        response = session.get(url, params=parameters)
        data = json.loads(response.text)
        return data
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)
        return {}
