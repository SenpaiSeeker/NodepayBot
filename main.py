import asyncio
import re
import sys
import time
import uuid

from fake_useragent import UserAgent
from loguru import logger
import aiohttp
import pyfiglet
from pyfiglet import figlet_format
from termcolor import colored

logger.remove()
logger.add(
    sink=sys.stdout,
    format="<r>[Nodepay]</r> | <white>{time:YYYY-MM-DD HH:mm:ss}</white> | "
           "<level>{level: <7}</level> | <cyan>{line: <3}</cyan> | {message}",
colorize=True

)
logger = logger.opt(colors=True)

def print_header():
    ascii_art = figlet_format("NodepayBot", font="slant")
    
    colored_art = colored(ascii_art, color="cyan")
    
    border = "=" * 60
    
    print(border)
    print(colored_art)
    print("Welcome to NodepayBot - Automate your tasks effortlessly!")
    print(border)

print_header()

def read_tokens_and_proxy():
    with open('tokens.txt', 'r') as file:
        tokens_content = sum(1 for line in file)

    with open('proxy.txt', 'r') as file:
        proxy_count = sum(1 for line in file)

    return tokens_content, proxy_count

tokens_content, proxy_count = read_tokens_and_proxy()

print()
print(f"Tokens: {tokens_content}. | Loaded {proxy_count} proxies.\n")
print(f"Nodepay only supports 3 connections per account. Using too many proxies may cause issues.")
print()
print("=" * 60)


HIDE_PROXY = "[HIDDEN]"
PING_INTERVAL = 1
RETRIES_LIMIT = 60

# API Endpoints
DOMAIN_API_ENDPOINTS = {
    "SESSION": [
        "https://api.nodepay.ai/api/auth/session"
    ],
    "PING": [
        "http://13.215.134.222/api/network/ping"
    ]
}

CONNECTION_STATES = {
    "CONNECTED": 1,
    "DISCONNECTED": 2,
    "NO_CONNECTION": 3
}

status_connect = CONNECTION_STATES["NO_CONNECTION"]
browser_id = None
account_info = {}
last_ping_time = {}

def generate_uuid():
    return str(uuid.uuid4())

def validate_response(response):
    if not response or "code" not in response or response["code"] < 0:
        raise ValueError("Invalid response received from the server.")
    return response

async def initialize_profile(proxy, token):
    global browser_id, account_info
    try:
        session_info = load_session_info(proxy)

        if not session_info:
            browser_id = generate_uuid()
            response = await send_request(DOMAIN_API_ENDPOINTS["SESSION"][0], {}, proxy, token)
            validate_response(response)
            account_info = response["data"]

            if account_info.get("uid"):
                save_session_info(proxy, account_info)
                await start_ping_loop(proxy, token)
            else:
                handle_logout(proxy)
        else:
            account_info = session_info
            await start_ping_loop(proxy, token)
    except Exception as e:
        error_message = str(e)
        if "keepalive ping timeout" in error_message or "500 Internal Server Error" in error_message:
            remove_proxy(proxy)
        else:
            logger.error(f"Error: {error_message}")
            return proxy

async def send_request(url, payload, proxy, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": UserAgent().random,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://app.nodepay.ai",
        "Origin": "chrome-extension://lgmpfmgeabnnlemejacfljbmonaomfmm",
        "X-Requested-With": "NodepayExtension",
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers, proxy=proxy, timeout=60) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            error_code = getattr(e, 'status', 'Unknown')
            logger.error(f"<yellow>API Request Failed: {e.status}, Message: {e.message}</yellow>")
            raise ValueError(f"API request failed")

async def start_ping_loop(proxy, token):
    try:
        while True:
            await send_ping(proxy, token)
            await asyncio.sleep(PING_INTERVAL)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass

async def send_ping(proxy, token):
    global last_ping_time, RETRIES_LIMIT, status_connect
    last_ping_time[proxy] = time.time()

    try:
        data = {
            "id": account_info.get("uid"),
            "browser_id": browser_id,
            "timestamp": int(time.time())
        }

        response = await send_request(DOMAIN_API_ENDPOINTS["PING"][0], data, proxy, token)
        if response["code"] == 0:
            ip_address = HIDE_PROXY if not proxy else re.search(r'(?<=@)[^:]+', proxy).group()
            total_points_earned = response["data"].get("points", 0)  # Assuming 'points' is the key in the API response
            if proxy:
                logger.success(
                    f"<green>Ping Successful</green>, IP Score: <cyan>{response['data'].get('ip_score')}</cyan>, "
                    f"Proxy: <yellow>{ip_address}</yellow>, Total Points Earned: <blue>{total_points_earned}</blue>"
                )
            else:
                logger.success(
                    f"<green>Ping Successful</green>, IP Score: <cyan>{response['data'].get('ip_score')}</cyan>, "
                    f"IP: <yellow>{ip_address}</yellow>, Total Points Earned: <blue>{total_points_earned}</blue>"
                )
            RETRIES_LIMIT = 0
            status_connect = CONNECTION_STATES["CONNECTED"]
        else:
            handle_ping_failure(proxy, response)
    except Exception:
        handle_ping_failure(proxy, None)

def handle_ping_failure(proxy, response):
    global RETRIES_LIMIT, status_connect
    RETRIES_LIMIT += 1
    ip_address = HIDE_PROXY if not proxy else re.search(r'(?<=@)[^:]+', proxy).group()
    error_message = response.get("message") if response else "No response from server"

    if response and response.get("code") == 403:
        handle_logout(proxy)
        logger.warning(f"<yellow>Ping Failed: Unauthorized Access</yellow>, Proxy: <yellow>{ip_address}</yellow>")
    else:
        logger.error(f"<yellow>Ping Failed</yellow>, Proxy: <yellow>{ip_address}</yellow>, Reason: {error_message}")
        remove_proxy(proxy)
        status_connect = CONNECTION_STATES["DISCONNECTED"]

def handle_logout(proxy):
    global status_connect, account_info
    status_connect = CONNECTION_STATES["NO_CONNECTION"]
    account_info = {}
    save_status(proxy, None)

def load_proxies(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read().splitlines()
    except Exception:
        logger.error(f"Failed to load proxy list. Exiting.")
        raise SystemExit()

def save_session_info(proxy, data):
    pass

def load_session_info(proxy):
    return {}

def remove_proxy(proxy):
    pass

def ask_user_for_proxy():
    user_input = ""
    while user_input not in ['yes', 'no']:
        user_input = input("Do you want to use proxy? (yes/no)? ").strip().lower()
        if user_input not in ['yes', 'no']:
            print("Invalid input. Please enter 'yes' or 'no'.")
    print(f"You selected: {'Yes' if user_input == 'yes' else 'No'}, ENJOY!\n")
    return user_input == 'yes'

async def main():
    use_proxy = ask_user_for_proxy()

    proxies = load_proxies('proxy.txt') if use_proxy else []

    try:
        with open('tokens.txt', 'r') as file:
            tokens = file.read().splitlines()
    except FileNotFoundError:
        logger.error(f"tokens.txt not found. Ensure the file is in the correct directory.")
        exit()

    if not tokens:
        logger.error(f"No tokens provided. Exiting.")
        exit()

    token_proxy_pairs = [(tokens[i % len(tokens)], proxy) for i, proxy in enumerate(proxies)] if use_proxy else [(token, "") for token in tokens]

    tasks = [asyncio.create_task(initialize_profile(proxy, token)) for token, proxy in token_proxy_pairs]

    while True:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task encountered an error")
            else:
                logger.success(f"Task completed successfully")

        await asyncio.sleep(10)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning(f"Program terminated by user.")
