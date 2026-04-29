import asyncio
import aiohttp
import time
import random
from typing import Dict, Optional
from urllib.parse import urlparse, urljoin
import urllib.robotparser as urobot

from bs4 import BeautifulSoup


# ==========================================
# RATE LIMITER
# ==========================================

class RateLimiter:
    def __init__(self, requests_per_second: float = 1.0, per_domain: bool = True):
        self.rps = requests_per_second
        self.per_domain = per_domain

        self.last_request_time: Dict[str, float] = {}
        self.global_last_time = 0

        self.lock = asyncio.Lock()

    async def acquire(self, domain: str = None):
        async with self.lock:
            now = time.time()

            if self.per_domain and domain:
                last = self.last_request_time.get(domain, 0)
            else:
                last = self.global_last_time

            wait_time = max(0, (1 / self.rps) - (now - last))

            if wait_time > 0:
                await asyncio.sleep(wait_time)

            if self.per_domain and domain:
                self.last_request_time[domain] = time.time()
            else:
                self.global_last_time = time.time()


# ==========================================
# ROBOTS.TXT
# ==========================================

class RobotsParser:
    def __init__(self):
        self.parsers: Dict[str, urobot.RobotFileParser] = {}

    async def fetch_robots(self, base_url: str):
        domain = urlparse(base_url).netloc

        if domain in self.parsers:
            return self.parsers[domain]

        robots_url = f"{urlparse(base_url).scheme}://{domain}/robots.txt"

        parser = urobot.RobotFileParser()
        parser.set_url(robots_url)

        try:
            parser.read()
        except Exception:
            pass

        self.parsers[domain] = parser
        return parser

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        domain = urlparse(url).netloc
        parser = self.parsers.get(domain)

        if not parser:
            return True

        return parser.can_fetch(user_agent, url)

    def get_crawl_delay(self, user_agent: str = "*") -> float:
        for parser in self.parsers.values():
            delay = parser.crawl_delay(user_agent)
            if delay:
                return delay
        return 0


# ==========================================
# HTML PARSER
# ==========================================

class HTMLParser:
    def parse(self, html: str, base_url: str):
        soup = BeautifulSoup(html, "lxml")

        links = [
            urljoin(base_url, a.get("href"))
            for a in soup.find_all("a", href=True)
        ]

        return {
            "links": list(set(links))
        }


# ==========================================
# ASYNC CRAWLER
# ==========================================

class AsyncCrawler:
    def __init__(
        self,
        max_concurrent=5,
        requests_per_second=2.0,
        respect_robots=True,
        min_delay=0.5,
        user_agent="MyBot/1.0"
    ):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter(requests_per_second)
        self.robots = RobotsParser()
        self.parser = HTMLParser()

        self.min_delay = min_delay
        self.user_agent = user_agent
        self.respect_robots = respect_robots

        self.visited = set()
        self.blocked = 0
        self.start_time = time.time()

    async def _get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": self.user_agent}
            )
        return self.session

    async def fetch(self, url: str):
        domain = urlparse(url).netloc

        # robots.txt
        if self.respect_robots:
            parser = await self.robots.fetch_robots(url)

            if not parser.can_fetch(self.user_agent, url):
                print(f"🚫 blocked by robots.txt: {url}")
                self.blocked += 1
                return None

        # rate limit
        await self.rate_limiter.acquire(domain)

        # crawl delay
        delay = self.robots.get_crawl_delay(self.user_agent)
        if delay:
            await asyncio.sleep(delay)

        # jitter
        await asyncio.sleep(self.min_delay + random.uniform(0, 0.5))

        try:
            session = await self._get_session()

            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.text()

        except Exception as e:
            return None

    async def crawl(self, start_urls, max_pages=20):
        queue = asyncio.Queue()

        for url in start_urls:
            await queue.put(url)
            self.visited.add(url)

        results = {}

        async def worker():
            while not queue.empty():
                url = await queue.get()

                html = await self.fetch(url)
                if not html:
                    continue

                data = self.parser.parse(html, url)
                results[url] = data

                for link in data["links"]:
                    if link not in self.visited and len(self.visited) < max_pages:
                        self.visited.add(link)
                        await queue.put(link)

        workers = [asyncio.create_task(worker()) for _ in range(5)]

        while any(not w.done() for w in workers):
            elapsed = time.time() - self.start_time
            rps = len(results) / elapsed if elapsed > 0 else 0

            print(
                f"📊 pages={len(results)} "
                f"blocked={self.blocked} "
                f"speed={rps:.2f} req/sec"
            )

            await asyncio.sleep(1)

        await asyncio.gather(*workers)

        return results

    async def close(self):
        if self.session:
            await self.session.close()


# ==========================================
# DEMO
# ==========================================

async def main():
    crawler = AsyncCrawler(
        max_concurrent=5,
        requests_per_second=2.0,
        respect_robots=True,
        min_delay=0.5,
        user_agent="MyBot/1.0"
    )

    try:
        results = await crawler.crawl(
            start_urls=["https://httpbin.org/links/5/0"],
            max_pages=10
        )

        print(f"\n✅ Итог: {len(results)} страниц")

    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())