import asyncio
import sys
import time
import uuid
import json

from fake_useragent import UserAgent
from curl_cffi import requests
from loguru import logger
from pyfiglet import figlet_format
from termcolor import colored
from urllib.parse import urlparse

# Constants
PING_INTERVAL = 0.5
DOMAIN_API = {
    "SESSION": "http://api.nodepay.ai/api/auth/session",
    "PING": ["http://18.142.29.174/api/network/ping", "https://nw.nodepay.org/api/network/ping"]
}

# Global configuration
SHOW_REQUEST_ERROR_LOG = False


def print_header():
    ascii_art = figlet_format("NodepayBot", font="slant")
    colored_art = colored(ascii_art, color="white")
    border = "=" * 40
    
    print(border)
    print(colored_art)
    print(border)

print_header()

def load_proxies():
    try:
        with open('proxies.txt', 'r') as file:
            proxies = file.read().splitlines()
        return proxies
    except Exception as e:
        logger.error(f"Failed to load proxies: {e}")
        raise SystemExit("Exiting due to failure in loading proxies")

# Main functions
token_status = {}

def dailyclaim(token):
    try:
        url = f"https://api.nodepay.org/api/mission/complete-mission?"
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Origin": "https://app.nodepay.ai",
            "Referer": "https://app.nodepay.ai/"
        }
        data = {"mission_id": "1"}
        response = requests.post(url, headers=headers, json=data, impersonate="chrome110")

        if response.json().get('success'):
            if token_status.get(token) != "claimed":
                logger.info("<green>Claim Reward Success!</green>")
                token_status[token] = "claimed"
        else:
            if token_status.get(token) != "failed":
                logger.info("Reward Already Claimed! Or Something Wrong!")
                token_status[token] = "failed"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error : {e}")

async def call_api(url, data, token, proxy=None):
    user_agent = UserAgent().chrome if UserAgent().chrome else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    sec_ch_ua_version = user_agent.split("Chrome/")[-1].split(" ")[0]
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": user_agent,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://app.nodepay.ai/",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "chrome-extension://lgmpfmgeabnnlemejacfljbmonaomfmm",
        "Sec-Ch-Ua": f'"Chromium";v="{sec_ch_ua_version}", "Google Chrome";v="{sec_ch_ua_version}", "Not?A_Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "DNT": "1",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }

    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        response = requests.post(url, json=data, headers=headers, proxies=proxies, impersonate="chrome110", timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during API call: {e}")
        return None

def extract_proxy_ip(proxy_url):
    try:
        parsed_url = urlparse(proxy_url)
        return parsed_url.hostname
    except Exception as e:
        logger.warning(f"Failed to extract IP from proxy: {proxy_url}, error: {e}")
        return "Unknown"

async def start_ping(token, account_info, proxy):
    browser_id = str(uuid.uuid4())
    url_index = 0
    while True:
        try:
            url = random.choice(DOMAIN_API["PING"])
            data = {
                "id": account_info.get("uid"),
                "browser_id": browser_id,
                "timestamp": int(time.time())
            }
            response = await call_api(url, data, token, proxy)

            if response:
                response_data = response.get("data", {})
                ip_score = response_data.get("ip_score", "Unavailable")

                if proxy:
                    proxy_ip = extract_proxy_ip(proxy)
                    logger.info(
                        f"<green>Ping Successful</green>, IP Score: <cyan>{ip_score}</cyan>, Proxy: <cyan>{proxy_ip}</cyan>"
                    )
                else:
                    ip_address = get_ip_address()
                    logger.info(
                        f"Ping Successful, IP Score: {ip_score}, IP Address: {ip_address}"
                    )
            else:
                logger.warning(f"No response from {url}")
        except Exception as e:
            pass
        

def log_user_data(user_data):
    try:
        name = user_data.get("name", "Unknown")
        balance = user_data.get("balance", {})
        current_amount = balance.get("current_amount", 0)
        total_collected = balance.get("total_collected", 0)

        log_message = (
            f"{name}, "
            f"Current Amount: {current_amount}, Total Collected: {total_collected}"
        )
        logger.info(f"Name: {log_message}")
    except Exception as e:
        logger.error(f"Failed to log user data: {e}")

async def process_account(token, proxies):
    try:
        response = await call_api(DOMAIN_API["SESSION"], {}, token, proxies)
        if response and response.get("code") == 0:
            account_info = response["data"]
            log_user_data(account_info)
            return await start_ping(token, account_info, proxies)
        else:
            logger.warning(f"Invalid or no response for token with proxy {proxies}")
    except Exception as e:
        logger.error(f"Unhandled error with proxy {proxy} for token {token}: {e}")

async def main():
    proxies = load_proxies()
    try:
        with open('tokens.txt', 'r') as file:
            tokens = file.read()
    except FileNotFoundError:
        print("File tokens.txt not found. Please create it.")
        exit()

    tasks = []
    for proxy in proxies:
        tasks.append(process_account(tokens, proxy))

    await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program terminated by user.")
