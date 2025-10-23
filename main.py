import ccxt
import os
import json
import requests
import time
import traceback
import random
import tweepy
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from web3 import Web3

# === CONFIGURATION ===

# Load Exchanges
exchanges = {
    'bybit': ccxt.bybit({
        'apiKey': os.getenv('BYBIT_KEY'),
        'secret': os.getenv('BYBIT_SECRET'),
        'enableRateLimit': True
    }),
    'mexc': ccxt.mexc({
        'apiKey': os.getenv('MEXC_KEY'),
        'secret': os.getenv('MEXC_SECRET'),
        'enableRateLimit': True
    }),
    'bitget': ccxt.bitget({
        'apiKey': os.getenv('BITGET_KEY'),
        'secret': os.getenv('BITGET_SECRET'),
        'enableRateLimit': True
    })
}

# Sandbox Mode Toggle
if os.getenv('SANDBOX', 'True') == 'True':
    for ex in exchanges.values():
        try:
            ex.set_sandbox_mode(True)
        except Exception as e:
            print(f"[!] Sandbox not supported: {ex.id}")

# Wallet + Web3
infura_url = f"https://mainnet.infura.io/v3/{os.getenv('INFURA_KEY')}"
w3 = Web3(Web3.HTTPProvider(infra_url))
wallet = w3.eth.account.from_key(os.getenv('WALLET_PRIVATE_KEY'))
wallet_address = wallet.address

# Google Sheets
creds = Credentials.from_service_account_info(json.loads(os.getenv('CREDENTIALS_JSON')))
sheets_service = build('sheets', 'v4', credentials=creds)
sheet_id = os.getenv('SHEET_ID')

# X/Twitter API v2 Setup
auth = tweepy.OAuth1UserHandler(
    os.getenv('X_CONSUMER_KEY'),
    os.getenv('X_CONSUMER_SECRET'),
    os.getenv('X_ACCESS_TOKEN'),
    os.getenv('X_ACCESS_TOKEN_SECRET')
)
api = tweepy.API(auth)
client = tweepy.Client(
    bearer_token=os.getenv('X_BEARER_TOKEN'),
    consumer_key=os.getenv('X_CONSUMER_KEY'),
    consumer_secret=os.getenv('X_CONSUMER_SECRET'),
    access_token=os.getenv('X_ACCESS_TOKEN'),
    access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET')
)

# === CORE FUNCTIONS ===

def fetch_deep_links(network):
    try:
        if network == 'awin':
            url = f"https://api.awin.com/advertisers/{os.getenv('AWIN_ADVERTISER_ID')}/links"
            headers = {'Authorization': f'Bearer {os.getenv("AWIN_KEY")}'}
            data = requests.get(url, headers=headers).json()
            return [link['url'] for link in data if 'deep' in link.get('type', '')]
        elif network == 'rakuten':
            url = f"https://api.linksynergy.com/linklocator/1.0/getlinks"
            params = {
                "token": os.getenv('RAKUTEN_WEBSERVICE_TOKEN'),
                "scope": os.getenv('RAKUTEN_SCOPE_ID'),
                "security": os.getenv('RAKUTEN_SECURITY_TOKEN')
            }
            data = requests.get(url, params=params).json()
            return [link['link'] for link in data.get('links', [])]
    except Exception as e:
        print(f"[DeepLink Error] {e}")
        return []

def execute_arbitrage():
    try:
        for ex in exchanges.values():
            balance = ex.fetch_balance()['total'].get('USDT', 0)
            for pair in ['HEX/USDT', 'ETH/USDT', 'SOL/USDT']:
                orderbook = ex.fetch_order_book(pair)
                bid = orderbook['bids'][0][0] if orderbook['bids'] else None
                ask = orderbook['asks'][0][0] if orderbook['asks'] else None
                if bid and ask and (ask - bid) / bid > 0.01:
                    amount = min(balance * 0.01 / ask, 100)
                    ex.create_order(pair, 'limit', 'buy', amount, ask)
                    ex.create_order(pair, 'limit', 'sell', amount, bid)
                    print(f"[Arbitrage] {pair}: executed {amount} units profit ${amount * (bid - ask):.2f}")
    except Exception:
        print(traceback.format_exc())

def execute_defi():
    try:
        if w3.is_connected():
            balance = w3.eth.get_balance(wallet_address) / 10**18
            if balance > 0.01:
                print(f"[DeFi] Deposited {balance:.4f} ETH to Pendle/Aave simulation.")
    except Exception:
        print(traceback.format_exc())

def log_to_sheets(data):
    try:
        sheets_service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="A:A",
            valueInputOption="RAW",
            body={"values": [[data]]}
        ).execute()
        print(f"[Sheets] Logged: {data}")
    except Exception:
        print(traceback.format_exc())

def send_whatsapp_alert(message):
    try:
        zapier_webhook = os.getenv('ZAPIER_WEBHOOK')
        payload = {'value1': message}
        res = requests.post(zapier_webhook, json=payload)
        if res.status_code != 200:
            print(f"[WhatsApp] Error | Status: {res.status_code} | Response: {res.text}")
        else:
            print(f"[WhatsApp] Sent | Status: {res.status_code}")
    except Exception as e:
        print(f"[WhatsApp Error] {e}")

def post_to_x(message):
    try:
        api.update_status(message[:280])  # X limit 280 chars
        print(f"[X/Twitter] Posted: {message}")
    except Exception as e:
        print(f"[X Error] {e}")

def post_to_telegram(message):
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message[:4096]}  # Telegram limit 4096 chars
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"[Telegram] Error | Status: {res.status_code} | Response: {res.text}")
        else:
            print(f"[Telegram] Sent | Status: {res.status_code}")
    except Exception as e:
        print(f"[Telegram Error] {e}")

def auto_post_affiliate_links():
    try:
        # Fetch AWIN deep links
        awin_links = fetch_deep_links('awin')
        # Fetch Rakuten deep links
        rakuten_links = fetch_deep_links('rakuten')

        all_links = awin_links + rakuten_links

        if not all_links:
            print("No affiliate links found this cycle.")
            return

        # Choose a few to post each cycle (randomized)
        links_to_post = random.sample(all_links, min(3, len(all_links)))

        for link in links_to_post:
            message = f"🔥 Check out our latest affiliate deal! {link} 💰 #Affiliate #Deals #Crypto #AI"

            # Post to X (Twitter)
            post_to_x(message)

            # Post to Telegram
            post_to_telegram(message)

            # Send WhatsApp alert (Zapier)
            send_whatsapp_alert(message)

            # Log link to Google Sheets
            log_to_sheets(f"Affiliate Posted: {link}")

            print(f"[Affiliate] Posted link: {link}")

    except Exception as e:
        print(f"[Affiliate AutoPost Error] {e}")

# === MAIN LOOP ===
def main():
    while True:
        try:
            total_balance = sum(ex.fetch_balance()['total'].get('USDT', 0) for ex in exchanges.values())
            trades = sum(len(ex.fetch_open_orders()) for ex in exchanges.values())
            forecast = total_balance * 0.1
            data = f"${total_balance:.2f} | Trades: {trades} | Forecast: ${forecast:.2f}"
            
            log_to_sheets(data)
            send_whatsapp_alert(f"OmniPredatorV4-AffiliateApex | Amson Multi Global LTD: {data}")
            execute_arbitrage()
            execute_defi()
            post_to_x(f"🚀 OmniPredatorV4 Daily Report:\n{data}\n#Crypto #DeFi #Automation #AI")
            post_to_telegram(f"📊 OmniPredatorV4 Update:\n{data}")
            auto_post_affiliate_links()
            time.sleep(3600)  # 1-hour cycle
        except Exception:
            print(traceback.format_exc())
            time.sleep(60)

if __name__ == "__main__":
    main()
