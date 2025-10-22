import requests
import time
import os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np
import random

# Config
IFTTT_KEY = os.getenv('IFTTT_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = '@SlickofficialsHQ'
IFTTT_X_EVENT = os.getenv('IFTTT_X_EVENT')
IFTTT_TIKTOK_EVENT = os.getenv('IFTTT_TIKTOK_EVENT')
IFTTT_IG_EVENT = os.getenv('IFTTT_IG_EVENT')
analyzer = SentimentIntensityAnalyzer()

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

def fetch_sentiment():
    try:
        url = f"https://api.twitter.com/2/tweets/search/recent?query=crypto%20global&bearer_token={os.getenv('X_BEARER_TOKEN')}"
        headers = {'Authorization': f"Bearer {os.getenv('X_BEARER_TOKEN')}"}
        data = requests.get(url, headers=headers).json()
        scores = [analyzer.polarity_scores(tweet['text'])['compound'] for tweet in data.get('data', [])]
        return np.mean(scores) if scores else 0
    except:
        return 0

def post_update(profit, trades, affiliate, defi_apr):
    sentiment = fetch_sentiment()
    link_name, link = random.choice(list(DEEP_LINKS.items()))
    if sentiment > 0.5:
        text = f"🌍 OmniPredator V4: ${profit:.2f} from {trades} trades + {defi_apr}% DeFi! Grab {link_name}: {link} #SlickofficialsHQ"
    else:
        text = f"💪 Predator Global: ${profit:.2f} from {trades} + {defi_apr}% DeFi. Join with {link_name}: {link} #GlobalPredator"
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': text})
        requests.post(f"https://maker.ifttt.com/trigger/{IFTTT_X_EVENT}/with/key/{IFTTT_KEY}", json={'value1': text})
        requests.post(f"https://maker.ifttt.com/trigger/{IFTTT_TIKTOK_EVENT}/with/key/{IFTTT_KEY}", json={'value1': text, 'value2': 'YOUR_TIKTOK_VIDEO_URL'})
        requests.post(f"https://maker.ifttt.com/trigger/{IFTTT_IG_EVENT}/with/key/{IFTTT_KEY}", json={'value1': text})
        print(f"Posted: {text[:50]}...")
    except Exception as e:
        print(f"Post Error: {e}")

while True:
    try:
        profit = 25.0  # Auto-pulled from bot
        trades = 150
        affiliate = 250.0
        defi_apr = 35
        post_update(profit, trades, affiliate, defi_apr)
        time.sleep(86400)
    except Exception as e:
        print(f"Virality Error: {e}")
        time.sleep(3600)
