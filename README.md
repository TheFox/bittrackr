# BitTrackr — Get your FOMO on the Command-line

## BitTracker

```bash
./bin/bittrackr.sh -c var/config.json -i 50 -u 60
```

## Dev

- <https://en.wikipedia.org/wiki/ANSI_escape_code>

```bash
curl -H 'X-CMC_PRO_API_KEY: b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c' -H 'Accept: application/json' -d 'start=1&limit=5000&convert=USD' -G https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest

curl -H 'X-CMC_PRO_API_KEY: b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c' -H 'Accept: application/json' 'https://sandbox-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?symbol=BTC,ETH' | jq
```
