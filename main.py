import asyncio
import time
import uuid
import random

from fake_useragent import UserAgent
import aiohttp
from loguru import logger
from pyfiglet import figlet_format
from termcolor import colored

DOMAIN_API = {
    "SESSION": "http://api.nodepay.ai/api/auth/session",
    "PING": ["http://18.142.29.174/api/network/ping", "https://nw.nodepay.org/api/network/ping"]
}
HEADERS_COMMON = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "DNT": "1",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}
REQUEST_TIMEOUT = 30

def print_header():
    ascii_art = figlet_format("NodepayBot", font="slant")
    colored_art = colored(ascii_art, color="white")
    border = "=" * 70
    print(f"{colored(border, color='white')}\n{colored_art}\n{colored(border, color='white')}")

def load_file(filename):
    try:
        with open(filename, 'r') as file:
            return file.read().splitlines()
    except FileNotFoundError:
        logger.error(f"File '{filename}' not found. Please create it.")
        raise SystemExit

async def call_api(url, data, token, proxy):
    user_agent = UserAgent()
    headers = {
        **HEADERS_COMMON,
        "Authorization": f"Bearer {token}",
        "User-Agent": user_agent.random,
        "Referer": "https://app.nodepay.ai/",
    }
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.post(
                url,
                json=data,
                headers=headers,
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API call error: {e}")
            return None

async def process_ping(token, account_info, proxy):
    browser_id = str(uuid.uuid4())
    url = random.choice(DOMAIN_API["PING"])
    data = {
        "id": account_info.get("uid"),
        "browser_id": browser_id,
        "timestamp": int(time.time())
    }
    response = await call_api(url, data, token, proxy)
    if response:
        ip_score = response.get("data", {}).get("ip_score", "Unavailable")
        logger.info(f"Ping Successful, IP Score: {ip_score}, Proxy: {proxy}")
    else:
        logger.warning(f"Ping failed for Proxy: {proxy}")

async def process_account(token, proxy):
    session_response = await call_api(DOMAIN_API["SESSION"], {}, token, proxy)
    if session_response and session_response.get("code") == 0:
        account_info = session_response["data"]
        data_account = [f"{i}: {x['total_collected'] if i == 'balance' else x}" for i, x in account_info.items() if i not in ["avatar", "network_earning_rate", "referral_link"]]
        logger.info("Account info:")
        for x in data_account:
            logger.info(x)
        await process_ping(token, account_info, proxy)
    else:
        logger.warning(f"Failed to process token {token} with proxy {proxy}")

async def main():
    print_header()
    proxies = load_file("proxies.txt")
    tokens = load_file("tokens.txt")
    tasks = [process_account(token, proxy) for token in tokens for proxy in proxies]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program terminated by user.")
