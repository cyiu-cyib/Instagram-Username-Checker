import asyncio
import os
import re
import sys
import argparse
from typing import List, Tuple

import aiohttp
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

DEFAULT_INPUT = os.getenv('INPUT_FILE', 'usernames.txt')
DEFAULT_OUTPUT = os.getenv('OUTPUT_FILE', 'hits.txt')
DEFAULT_CONCURRENCY = int(os.getenv('CONCURRENCY', '50'))
DEFAULT_RETRIES = int(os.getenv('RETRIES', '3'))
DEFAULT_TIMEOUT = int(os.getenv('TIMEOUT', '30'))
OXY_URL = 'https://realtime.oxylabs.io/v1/queries'


def open_file(path: str = DEFAULT_INPUT) -> List[str]:
    if not os.path.exists(path):
        print(f'[ERROR] Input file not found: {path}')
        return []
    with open(path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    # keep order but drop duplicates
    seen, result = set(), []
    for name in lines:
        if name not in seen:
            result.append(name)
            seen.add(name)
    return result


def write_file(arg: str, path: str = DEFAULT_OUTPUT) -> None:
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f'{arg}\n')


def is_valid_instagram_username(username: str) -> bool:
    # Instagram: 1-30 chars; letters, numbers, underscores, periods
    # We also ensure it doesn't start with a period and doesn't end with a period
    if not (1 <= len(username) <= 30):
        return False
    if not re.fullmatch(r'[A-Za-z0-9._]+', username):
        return False
    if username.startswith('.') or username.endswith('.'):
        return False
    return True


class OxylabsClient:
    def __init__(self, username: str, password: str, timeout: int = 30):
        self.auth = aiohttp.BasicAuth(username, password)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: aiohttp.ClientSession | None = None
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout, headers=self.headers, auth=self.auth)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def fetch_status_code(self, url: str) -> Tuple[int | None, dict | None]:
        assert self.session is not None
        payload = {
            'source': 'universal',
            'url': url,
            'parse': False
        }
        async with self.session.post(OXY_URL, json=payload) as resp:
            data = await resp.json(content_type=None)
            # structure can be either direct or wrapped in 'results'
            result = None
            if isinstance(data, dict) and 'results' in data and data.get('results'):
                result = data['results'][0]
            else:
                result = data
            status_code = None
            if isinstance(result, dict):
                status_code = result.get('status_code') or result.get('status')
            return status_code, result


class DirectClient:
    HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36'}

    def __init__(self, timeout: int = 15):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.HEADERS, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def fetch_status_code(self, url: str) -> Tuple[int | None, dict | None]:
        assert self.session is not None
        async with self.session.get(url) as resp:
            # We do not need full body; status is enough
            _ = await resp.text()
            return resp.status, None


class Checker:
    def __init__(
        self,
        usernames: List[str],
        oxylabs_username: str | None = None,
        oxylabs_password: str | None = None,
        concurrency: int = 20,
        retries: int = 3,
        output_path: str = DEFAULT_OUTPUT,
        request_timeout: int = 30,
    ):
        self.to_check = usernames
        self.sem = asyncio.Semaphore(max(1, concurrency))
        self.retries = max(0, retries)
        self.output_path = output_path
        self.oxy_user = oxylabs_username
        self.oxy_pass = oxylabs_password
        self.request_timeout = request_timeout

    async def _check_one(self, client, username: str) -> None:
        url = f'https://www.instagram.com/{username}/'
        attempt = 0
        while True:
            attempt += 1
            try:
                async with self.sem:
                    status_code, raw = await client.fetch_status_code(url)
                if status_code == 404:
                    print(f'\u001b[32;1m[AVAILABLE]\u001b[0m {url}')
                    write_file(username, self.output_path)
                elif status_code is None:
                    print(f'[!] Unknown status for {username}, response malformed: {raw!r}')
                else:
                    print(f'\u001b[31;1m[UNAVAILABLE]\u001b[0m {url} (status={status_code})')
                return
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt <= self.retries:
                    await asyncio.sleep(min(2 ** (attempt - 1), 10))
                    continue
                print(f'[ERROR] {username}: {e}')
                return

    async def start(self) -> None:
        valid_usernames = [u for u in self.to_check if is_valid_instagram_username(u)]
        skipped = [u for u in self.to_check if u not in valid_usernames]
        if skipped:
            print(f'[i] Skipping {len(skipped)} invalid usernames')
        if not valid_usernames:
            print('[i] No valid usernames to check.')
            return

        if self.oxy_user and self.oxy_pass:
            print('[i] Using Oxylabs Real-Time Crawler API')
            async with OxylabsClient(self.oxy_user, self.oxy_pass, timeout=self.request_timeout) as client:
                tasks = [asyncio.create_task(self._check_one(client, u)) for u in valid_usernames]
                await asyncio.gather(*tasks)
        else:
            print('[i] Oxylabs credentials not provided. Falling back to direct requests (may be inaccurate).')
            async with DirectClient(timeout=self.request_timeout) as client:
                tasks = [asyncio.create_task(self._check_one(client, u)) for u in valid_usernames]
                await asyncio.gather(*tasks)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Instagram Username Availability Checker with Oxylabs integration')
    parser.add_argument('-i', '--input', default=DEFAULT_INPUT, help='Path to input usernames file (overrides INPUT_FILE in .env)')
    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT, help='Path to output file for available usernames (overrides OUTPUT_FILE in .env)')
    parser.add_argument('-c', '--concurrency', type=int, default=DEFAULT_CONCURRENCY, help='Max concurrent checks (default from CONCURRENCY in .env, default 50)')
    parser.add_argument('--retries', type=int, default=DEFAULT_RETRIES, help='Retry attempts on transient errors (default from RETRIES in .env)')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT, help='Request timeout in seconds (default from TIMEOUT in .env)')
    parser.add_argument('--oxylabs-username', default=os.getenv('OXYLABS_USERNAME'), help='Oxylabs API username (or set OXYLABS_USERNAME in .env)')
    parser.add_argument('--oxylabs-password', default=os.getenv('OXYLABS_PASSWORD'), help='Oxylabs API password (or set OXYLABS_PASSWORD in .env)')
    return parser.parse_args(argv)


async def amain(argv: List[str]) -> None:
    args = parse_args(argv)
    usernames = open_file(args.input)
    checker = Checker(
        usernames=usernames,
        oxylabs_username=args.oxylabs_username,
        oxylabs_password=args.oxylabs_password,
        concurrency=args.concurrency,
        retries=args.retries,
        output_path=args.output,
        request_timeout=args.timeout,
    )
    await checker.start()


def main() -> None:
    try:
        asyncio.run(amain(sys.argv[1:]))
    except KeyboardInterrupt:
        print('\n[!] Interrupted by user')


if __name__ == '__main__':
    main()
