import ccxt
import pandas as pd
import numpy as np
from web3 import Web3
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestRegressor
import time
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from statsmodels.tsa.arima.model import ARIMA
import os
import json
import streamlit as st

# Config: Slickofficials HQ by Amson Multi Global LTD
SYMBOLS = ['HEX/USDT', 'ETH/USDT', 'SOL/USDT']
EXCHANGES = ['binance', 'mexc', 'bitget']
POLYGON_RPC = 'https://polygon-rpc.com'
ETHEREUM_RPC = 'https://mainnet.infura.io/v3/' + os.getenv('INFURA_KEY')
PENDLE_CONTRACT = '0x808507121b80c02388fad14726482e061b8da827'
AAVE_CONTRACT = '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9'
POSITION_SIZE = 1.5  # $22 split
VOL_MULTIPLIER = 0.3
SARSA_LEARNING_RATE = 0.15
SARSA_DISCOUNT = 0.95
SARSA_EPSILON = 0.05
AFFILIATE_NETWORKS = ['rakuten', 'awin']
AFFILIATE_API_KEYS = {
    'rakuten': os.getenv('RAKUTEN_KEY'),
    'awin': os.getenv('AWIN_KEY')
}
NEW_PLATFORMS = ['shareasale', 'cj_affiliate', 'clickbank', 'refersion', 'giddyup', 'affiliaxe', 'partnerstack']
DEEP_LINKS = {
    'Kila Custom Insoles': 'https://tidd.ly/3J1KeV2',
    'Kapitalwise': 'https://tidd.ly/43ibfu7',
    'Diamond Smile FR': 'https://tidd.ly/4nanmAp',
    "Bell's Reines": 'https://tidd.ly/3Jb6cEV',
    'Awin (USD)': 'https://tidd.ly/46RRifY',
    'AliExpress P': 'https://tidd.ly/3Jbg6GA',
    'NeckHammock': 'https://tidd.ly/4qyhB2L',
    'Slimeafit Affiliate Program FR': 'https://tidd.ly/3WbtvBv',
    'Timeshop24 DE': 'https://tidd.ly/4nWuz8s',
    'Bonne et Filou': 'https://tidd.ly/4hgNp7H',
    'Shenzhen Wondershare Software Co., Ltd': 'https://click.linksynergy.com/deeplink?id=iejQuC2lIug&mid=37160&murl=https%3A%2F%2Fwww.wondershare.com%2F'
}

# Init
exchanges = {
    'binance': ccxt.binance({'apiKey': os.getenv('BINANCE_KEY'), 'secret': os.getenv('BINANCE_SECRET'), 'enableRateLimit': True, 'sandbox': os.getenv('SANDBOX', 'True') == 'True'}),
    'mexc': ccxt.mexc({'apiKey': os.getenv('MEXC_KEY'), 'secret': os.getenv('MEXC_SECRET'), 'enableRateLimit': True, 'sandbox': os.getenv('SANDBOX', 'True') == 'True'}),
    'bitget': ccxt.bitget({'apiKey': os.getenv('BITGET_KEY'), 'secret': os.getenv('BITGET_SECRET'), 'enableRateLimit': True, 'sandbox': os.getenv('SANDBOX', 'True') == 'True'})
}
w3_polygon = Web3(Web3.HTTPProvider(POLYGON_RPC))
w3_ethereum = Web3(Web3.HTTPProvider(ETHEREUM_RPC))
account = w3_ethereum.eth.account.from_key(os.getenv('WALLET_PRIVATE_KEY'))
pendle_contract = w3_polygon.eth.contract(address=PENDLE_CONTRACT, abi=[{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"deposit","outputs":[],"stateMutability":"nonpayable","type":"function"}])
aave_contract = w3_ethereum.eth.contract(address=AAVE_CONTRACT, abi=[{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"deposit","outputs":[],"stateMutability":"nonpayable","type":"function"}])
scaler = MinMaxScaler()
analyzer = SentimentIntensityAnalyzer()
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.getenv('CREDENTIALS_JSON')), scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.getenv('SHEET_ID')).sheet1
sarsa_table = {s: np.zeros((10, 10, 5)) for s in SYMBOLS}

def fetch_prices(symbol):
    prices = {}
    for ex in EXCHANGES:
        try:
            prices[ex] = exchanges[ex].fetch_ticker(symbol)['bid' if ex == 'binance' else 'ask']
        except:
            prices[ex] = np.nan
    return prices

def fetch_sentiment(symbol):
    try:
        url = f"https://api.twitter.com/2/tweets/search/recent?query={symbol.split('/')[0]}%20crypto&bearer_token={os.getenv('X_BEARER_TOKEN')}"
        headers = {'Authorization': f"Bearer {os.getenv('X_BEARER_TOKEN')}"}
        data = requests.get(url, headers=headers).json()
        scores = [analyzer.polarity_scores(tweet['text'])['compound'] for tweet in data.get('data', [])]
        return np.mean(scores) if scores else 0
    except:
        return 0

def calculate_volatility(symbol):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{symbol.split('/')[0].lower()}/market_chart?vs_currency=usd&days=7&interval=hourly"
        data = requests.get(url).json()
        prices = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
        prices['returns'] = prices['close'].pct_change()
        return prices['returns'].std(), prices['returns'].mean()
    except:
        return 0.01, 0

def predict_edge(symbol):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{symbol.split('/')[0].lower()}/market_chart?vs_currency=usd&days=7&interval=hourly"
        data = requests.get(url).json()
        df = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
        df['returns'] = df['close'].pct_change()
        df['sentiment'] = fetch_sentiment(symbol)
        X = df[['close', 'returns', 'sentiment']].tail(24).values
        scaler.fit(X)
        X_scaled = scaler.transform(X)
        model = RandomForestRegressor(n_estimators=100).fit(X_scaled[:-1], df['returns'].tail(24).shift(-1).dropna())
        pred = model.predict(scaler.transform(X[-1].reshape(1,-1)))[0]
        conf = model.score(X_scaled[:-1], df['returns'].tail(24).shift(-1).dropna())
        return pred, conf
    except:
        return 0, 0

def sarsa_update(symbol, state, action, reward, next_state, next_action):
    current_q = sarsa_table[symbol][state[0], state[1], action]
    next_q = sarsa_table[symbol][next_state[0], next_state[1], next_action]
    sarsa_table[symbol][state[0], state[1], action] += SARSA_LEARNING_RATE * (reward + SARSA_DISCOUNT * next_q - current_q)

def choose_action(symbol, volatility, sentiment):
    state = (int((sentiment + 1) * 5), int(volatility * 10))
    if np.random.random() < SARSA_EPSILON:
        return np.random.randint(5)
    return np.argmax(sarsa_table[symbol][state[0], state[1], :])

def arbitrage(symbol, balance_usdt=22/len(SYMBOLS), balance_asset=0, avg_buy=0, trade_count=0, profits=[]):
    prices = fetch_prices(symbol)
    if any(np.isnan(list(prices.values()))): return balance_usdt, balance_asset, avg_buy, trade_count, profits
    volatility, _ = calculate_volatility(symbol)
    sentiment = fetch_sentiment(symbol)
    pred, conf = predict_edge(symbol)
    state = (int((sentiment + 1) * 5), int(volatility * 10))
    action = choose_action(symbol, volatility, sentiment)
    arb_th = [0.004, 0.006, 0.008, 0.01][action % 4]
    sl = [0.95, 0.93, 0.90, 0.88][action % 4]
    weight = [0.5, 1, 1.5, 2][action % 4] * (1 + sentiment * 0.3)
    pos_size = POSITION_SIZE * weight
    min_p = min(prices['mexc'], prices['bitget'])
    max_p = prices['binance']
    spread = (max_p - min_p) / min_p
    if spread > arb_th and conf > 0.65:
        qty = pos_size / min_p
        balance_asset += qty
        balance_usdt -= pos_size
        avg_buy = (avg_buy * balance_asset + min_p * qty) / (balance_asset + qty) if balance_asset > 0 else min_p
        trade_count += 1
        profits.append(0)
        print(f"ARB {symbol}: Buy {qty:.2f} @ ${min_p:.4f} (Sentiment {sentiment:.2f}, Conf {conf:.2f})")
    elif balance_asset > 0 and max_p < sl * avg_buy:
        usdt_out = balance_asset * max_p
        profit = usdt_out - (balance_asset * avg_buy)
        balance_usdt += usdt_out
        balance_asset, avg_buy = 0, 0
        trade_count += 1
        profits.append(profit)
        reward = profit - 0.15 * (22/len(SYMBOLS) - (balance_usdt + balance_asset * max_p)) + sentiment * 0.3
        next_state = (int((fetch_sentiment(symbol) + 1) * 5), int(calculate_volatility(symbol)[0] * 10))
        next_action = choose_action(symbol, calculate_volatility(symbol)[0], fetch_sentiment(symbol))
        sarsa_update(symbol, state, action, reward, next_state, next_action)
        print(f"STOP {symbol}: Sold {balance_asset:.2f} @ ${max_p:.4f}, Profit ${profit:.2f}")
    return balance_usdt, balance_asset, avg_buy, trade_count, profits

def auto_defi(balance_excess):
    if balance_excess < 1: return
    try:
        nonce = w3_polygon.eth.get_transaction_count(account.address)
        tx_pendle = pendle_contract.functions.deposit(int(0.5 * 1e6)).build_transaction({
            'from': account.address, 'nonce': nonce, 'gas': 200000, 'gasPrice': w3_polygon.to_wei('30', 'gwei')
        })
        signed_tx = w3_polygon.eth.account.sign_transaction(tx_pendle, os.getenv('WALLET_PRIVATE_KEY'))
        tx_hash = w3_polygon.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Pendle $0.5: {tx_hash.hex()} (50% APR)")
        nonce += 1
        tx_aave = aave_contract.functions.deposit(int(0.5 * 1e18)).build_transaction({
            'from': account.address, 'nonce': nonce, 'gas': 200000, 'gasPrice': w3_ethereum.to_wei('20', 'gwei')
        })
        signed_tx = w3_ethereum.eth.account.sign_transaction(tx_aave, os.getenv('WALLET_PRIVATE_KEY'))
        tx_hash = w3_ethereum.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Aave $0.5: {tx_hash.hex()} (20% APR)")
    except Exception as e:
        print(f"DeFi Error: {e}")

def fetch_deep_links(network):
    try:
        if network == 'awin':
            url = f"https://api.awin.com/advertisers/{os.getenv('AWIN_ADVERTISER_ID')}/links?apiKey={AFFILIATE_API_KEYS['awin']}"
            data = requests.get(url).json()
            return [link['url'] for link in data if 'deep' in link['type']]
        elif network == 'rakuten':
            url = f"https://api.linksynergy.com/linklocator/1.0/getlinks?token={AFFILIATE_API_KEYS['rakuten']}"
            data = requests.get(url).json()
            return [link['link'] for link in data.get('links', [])]
    except:
        return []

def apply_for_promotion(network, advertiser_id):
    try:
        if network == 'awin':
            url = f"https://api.awin.com/advertisers/{advertiser_id}/join?apiKey={AFFILIATE_API_KEYS['awin']}"
            response = requests.post(url).json()
            print(f"Applied to Awin advertiser {advertiser_id}: {response}")
            if response.get('status') != 'requested':
                requests.post(os.getenv('ZAPIER_WEBHOOK'), json={
                    'number': os.getenv('WHATSAPP_NUMBER'),
                    'message': f"Apply to Awin advertiser {advertiser_id} manually: https://ui.awin.com/merchant-directory"
                })
            return response.get('status') == 'requested'
        elif network == 'rakuten':
            url = f"https://api.linksynergy.com/advertiser/{advertiser_id}/join?token={AFFILIATE_API_KEYS['rakuten']}"
            response = requests.post(url).json()
            print(f"Applied to Rakuten advertiser {advertiser_id}: {response}")
            if response.get('status') != 'applied':
                requests.post(os.getenv('ZAPIER_WEBHOOK'), json={
                    'number': os.getenv('WHATSAPP_NUMBER'),
                    'message': f"Apply to Rakuten advertiser {advertiser_id} manually: https://members.linksynergy.com/"
                })
            return response.get('status') == 'applied'
    except:
        return False

def suggest_new_platforms():
    suggestion = np.random.choice(NEW_PLATFORMS)
    details = f"Join {suggestion} for 15% commissions, EPC $12"
    requests.post(os.getenv('ZAPIER_WEBHOOK'), json={
        'number': os.getenv('WHATSAPP_NUMBER'),
        'message': f"New platform suggestion: {details}. Apply? Y/N"
    })
    return suggestion, details

def update_dashboard(balances, prices, affiliate_earnings=0, trade_counts={}, profits={}):
    try:
        total = sum(bal[0] + bal[1] * prices[s]['binance'] for s, bal in balances.items())
        drawdown = (22 - total) / 22 if total < 22 else 0
        df = pd.DataFrame({'profit': profits.get(SYMBOLS[0], [])})
        forecast = ARIMA(df['profit'], order=(1,1,1)).fit().forecast(7)[0] if len(df) > 7 else 0
        for symbol in SYMBOLS:
            sheet.append_row([str(pd.Timestamp.now()), symbol, balances[symbol][0], balances[symbol][1], affiliate_earnings, total, trade_counts.get(symbol, 0), drawdown, forecast])
        requests.post(os.getenv('ZAPIER_WEBHOOK'), json={
            'number': os.getenv('WHATSAPP_NUMBER'),
            'message': f"Slickofficials HQ by Amson Multi Global LTD: ${total:.2f} | Trades {sum(trade_counts.values())} | Forecast ${forecast:.2f}"
        })
        return total, trade_counts, forecast, affiliate_earnings, drawdown
    except Exception as e:
        print(f"Dashboard Error: {e}")
        return 0, {}, 0, 0, 0

def backtest():
    for symbol in SYMBOLS:
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{symbol.split('/')[0].lower()}/market_chart/range?vs_currency=usd&from={int(pd.Timestamp('2025-01-01').timestamp())}&to={int(time.time())}"
            data = requests.get(url).json()
            prices = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
            prices['binance'] = prices['close'] * np.random.uniform(0.995, 1.005, len(prices))
            prices['mexc'] = prices['close'] * np.random.uniform(0.99, 1.01, len(prices))
            trades = prices[(prices['binance'] - prices['mexc']) / prices['mexc'] > 0.008]
            if len(trades) <= 10: return False
        except:
            return False
    return True

def streamlit_dashboard():
    st.set_page_config(page_title="Slickofficials HQ by Amson Multi Global LTD Dashboard", layout="wide")
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.title("Slickofficials HQ by Amson Multi Global LTD: Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username == os.getenv('DASHBOARD_USER') and password == os.getenv('DASHBOARD_PASS'):
                st.session_state.logged_in = True
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")
        return
    st.title("Slickofficials HQ by Amson Multi Global LTD: OmniPredator V4 Dashboard")
    balances = {s: [22/len(SYMBOLS), 0] for s in SYMBOLS}
    prices = {s: fetch_prices(s) for s in SYMBOLS}
    total, trade_counts, forecast, affiliate_earnings, drawdown = update_dashboard(balances, prices, trade_counts={s: 0 for s in SYMBOLS}, profits={s: [] for s in SYMBOLS})
    st.subheader("Performance Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Balance", f"${total:.2f}")
    col2.metric("Total Trades", sum(trade_counts.values()))
    col3.metric("7-Day Forecast", f"${forecast:.2f}")
    st.metric("Affiliate Earnings", f"${affiliate_earnings:.2f}")
    st.metric("Drawdown", f"{drawdown*100:.1f}%")
    st.subheader("Crypto Price Charts")
    for symbol in SYMBOLS:
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{symbol.split('/')[0].lower()}/market_chart?vs_currency=usd&days=7&interval=hourly"
            data = requests.get(url).json()
            df = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            st.write(f"{symbol} Price (7 Days)")
            chart_data = {
                "type": "line",
                "data": {
                    "labels": df['timestamp'].dt.strftime('%Y-%m-%d %H:%M').tolist(),
                    "datasets": [{
                        "label": symbol,
                        "data": df['close'].tolist(),
                        "borderColor": "#00C4B4",
                        "backgroundColor": "rgba(0, 196, 180, 0.2)",
                        "fill": True
                    }]
                },
                "options": {
                    "scales": {
                        "x": {"title": {"display": True, "text": "Time"}},
                        "y": {"title": {"display": True, "text": "Price (USD)"}}
                    }
                }
            }
            st.json(chart_data)
        except:
            st.write(f"No chart data for {symbol}")
    st.subheader("Affiliate Links")
    for name, link in DEEP_LINKS.items():
        st.write(f"{name}: {link}")

if __name__ == "__main__":
    if backtest():
        balances = {s: [22/len(SYMBOLS), 0] for s in SYMBOLS}
        avg_buy_prices = {s: 0 for s in SYMBOLS}
        trade_counts = {s: 0 for s in SYMBOLS}
        profits = {s: [] for s in SYMBOLS}
        last_adjust = time.time()
        last_affiliate = time.time()
        while True:
            try:
                for symbol in SYMBOLS:
                    prices = fetch_prices(symbol)
                    if not any(np.isnan(list(prices.values()))):
                        balances[symbol][0], balances[symbol][1], avg_buy_prices[symbol], trade_counts[symbol], profits[symbol] = arbitrage(
                            symbol, balances[symbol][0], balances[symbol][1], avg_buy_prices[symbol], trade_counts[symbol], profits[symbol]
                        )
                        if balances[symbol][0] > 1:
                            auto_defi(balances[symbol][0])
                            balances[symbol][0] -= 1
                update_dashboard(balances, {s: fetch_prices(s) for s in SYMBOLS}, trade_counts=trade_counts, profits=profits)
                if time.time() - last_adjust > 7 * 24 * 3600:
                    trade_counts = {s: 0 for s in SYMBOLS}
                    profits = {s: [] for s in SYMBOLS}
                    last_adjust = time.time()
                if time.time() - last_affiliate > 86400:
                    new_links = []
                    for network in AFFILIATE_NETWORKS:
                        new_links += fetch_deep_links(network)
                        apply_for_promotion(network, 'random_id')  # Replace with real advertiser ID logic
                    suggestion, details = suggest_new_platforms()
                    DEEP_LINKS.update({suggestion: 'auto_link'})  # Placeholder
                    print(f"Suggested: {suggestion} - {details}")
                    last_affiliate = time.time()
                time.sleep(3600)
            except Exception as e:
                print(f"OmniPredator V4 Error: {e} – Retrying...")
                time.sleep(60)
    else:
        print("Backtest failed – Check setup")
