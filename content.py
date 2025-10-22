import requests
import os
import numpy as np
import time

# Config: OmniPredatorV4-AffiliateApex by Slickofficials HQ | Amson Multi Global LTD
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
POST_TEMPLATES = [
    "🚀 {product} is a game-changer! Grab it now: {link} #SlickofficialsHQ #Hustle",
    "💪 Level up with {product}! Shop here: {link} #AmsonMultiGlobal #AffiliateApex",
    "🔥 Don’t miss {product}! Click: {link} #SlickofficialsHQ #OmniPredatorV4",
    "🌟 {product} for the win! Get yours: {link} #HealthAndWealth #SlickofficialsHQ",
    "💸 {product} is calling! Shop now: {link} #AmsonMultiGlobal #CryptoHustle"
]
PLATFORMS = ['x', 'facebook', 'tiktok', 'instagram']
POST_FREQUENCY = 3600  # 1 hour

def post_to_platform(platform, message):
    try:
        ifttt_key = os.getenv('IFTTT_KEY')
        event = os.getenv(f'IFTTT_{platform.upper()}_EVENT')
        url = f"https://maker.ifttt.com/trigger/{event}/with/key/{ifttt_key}"
        payload = {'value1': message}
        response = requests.post(url, json=payload)
        print(f"Posted to {platform}: {message} | Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error posting to {platform}: {e}")
        return False

def main():
    while True:
        try:
            for _ in range(np.random.randint(1, 3)):  # 1-2 posts/hour
                product, link = np.random.choice(list(DEEP_LINKS.items()))
                template = np.random.choice(POST_TEMPLATES)
                message = template.format(product=product, link=link)
                for platform in PLATFORMS:
                    post_to_platform(platform, message)
            time.sleep(POST_FREQUENCY)
        except Exception as e:
            print(f"Content Error: {e} - Retrying...")
            time.sleep(60)

if __name__ == "__main__":
    main()
