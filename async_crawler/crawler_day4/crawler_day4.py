import asyncio
import aiohttp
import time
import random

from typing import Dict
from typing import Optional
from typing import List

from urllib.parse import urlparse
from urllib.parse import urljoin

import urllib.robotparser as urobot

from bs4 import BeautifulSoup


# =========================================================
# RATE LIMITER
# =========================================================

class RateLimiter:
    """
    Ограничение скорости запросов.

    Поддерживает:
    - global rate limit
    - per-domain rate limit
    """

    def __init__(
        self,
        requests_per_second: float = 1.0,
        per_domain: bool = True
    ):

        # =============================================
        # REQUESTS PER SECOND
        # =============================================

        self.rps = requests_per_second

        # =============================================
        # PER DOMAIN MODE
        # =============================================

        self.per_domain = per_domain

        # =============================================
        # LAST REQUEST TIMES
        # =============================================

        self.last_request_time: Dict[
            str,
            float
        ] = {}

        self.global_last_time = 0

        # =============================================
        # LOCK
        # =============================================

        self.lock = asyncio.Lock()

    # =====================================================
    # ACQUIRE
    # =====================================================

    async def acquire(
        self,
        domain: str = None
    ):
        """
        Ожидание перед следующим запросом.
        """

        async with self.lock:

            now = time.time()

            # =========================================
            # LAST REQUEST TIME
            # =========================================

            if self.per_domain and domain:

                last = self.last_request_time.get(
                    domain,
                    0
                )

            else:

                last = self.global_last_time

            # =========================================
            # WAIT TIME
            # =========================================

            wait_time = max(
                0,
                (1 / self.rps) - (now - last)
            )

            if wait_time > 0:

                await asyncio.sleep(wait_time)

            # =========================================
            # UPDATE TIMESTAMP
            # =========================================

            current_time = time.time()

            if self.per_domain and domain:

                self.last_request_time[domain] = (
                    current_time
                )

            else:

                self.global_last_time = current_time


# =========================================================
# ROBOTS.TXT PARSER
# =========================================================

class RobotsParser:
    """
    Асинхронная работа с robots.txt

    ВАЖНО:
    НЕ используем parser.read(),
    потому что это blocking IO.
    """

    def __init__(self):

        # =============================================
        # CACHE
        # =============================================

        self.parsers: Dict[
            str,
            urobot.RobotFileParser
        ] = {}

    # =====================================================
    # FETCH ROBOTS
    # =====================================================

    async def fetch_robots(
        self,
        session: aiohttp.ClientSession,
        base_url: str
    ):
        """
        Асинхронная загрузка robots.txt
        """

        parsed = urlparse(base_url)

        domain = parsed.netloc

        # =============================================
        # CACHE
        # =============================================

        if domain in self.parsers:

            return self.parsers[domain]

        # =============================================
        # ROBOTS URL
        # =============================================

        robots_url = (
            f"{parsed.scheme}"
            f"://{domain}/robots.txt"
        )

        parser = urobot.RobotFileParser()

        try:

            async with session.get(
                robots_url
            ) as response:

                text = await response.text()

                # =====================================
                # PARSE ROBOTS
                # =====================================

                parser.parse(
                    text.splitlines()
                )

        except Exception:

            pass

        # =============================================
        # CACHE SAVE
        # =============================================

        self.parsers[domain] = parser

        return parser

    # =====================================================
    # CAN FETCH
    # =====================================================

    def can_fetch(
        self,
        url: str,
        user_agent: str = "*"
    ) -> bool:
        """
        Проверка разрешения robots.txt
        """

        domain = urlparse(url).netloc

        parser = self.parsers.get(domain)

        if not parser:
            return True

        return parser.can_fetch(
            user_agent,
            url
        )

    # =====================================================
    # GET CRAWL DELAY
    # =====================================================

    def get_crawl_delay(
        self,
        domain: str,
        user_agent: str = "*"
    ) -> float:
        """
        Получение Crawl-delay.
        """

        parser = self.parsers.get(domain)

        if not parser:
            return 0

        delay = parser.crawl_delay(
            user_agent
        )

        return delay or 0


# =========================================================
# HTML PARSER
# =========================================================

class HTMLParser:
    """
    HTML parser.
    """

    def parse(
        self,
        html: str,
        base_url: str
    ) -> dict:

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        # =============================================
        # TITLE
        # =============================================

        title = (

            soup.title.string.strip()

            if soup.title and soup.title.string

            else ""
        )

        # =============================================
        # LINKS
        # =============================================

        links = [

            urljoin(
                base_url,
                a.get("href")
            )

            for a in soup.find_all(
                "a",
                href=True
            )
        ]

        return {

            "title": title,

            "links": list(set(links))
        }


# =========================================================
# ASYNC CRAWLER
# =========================================================

class AsyncCrawler:
    """
    Advanced async crawler.

    Возможности:
    - rate limit
    - robots.txt
    - crawl delay
    - jitter
    - live stats
    """

    def __init__(
        self,
        max_concurrent=5,
        requests_per_second=2.0,
        respect_robots=True,
        min_delay=0.5,
        user_agent="MyBot/1.0"
    ):

        # =============================================
        # SESSION
        # =============================================

        self.session: Optional[
            aiohttp.ClientSession
        ] = None

        # =============================================
        # RATE LIMITER
        # =============================================

        self.rate_limiter = RateLimiter(
            requests_per_second
        )

        # =============================================
        # ROBOTS
        # =============================================

        self.robots = RobotsParser()

        # =============================================
        # PARSER
        # =============================================

        self.parser = HTMLParser()

        # =============================================
        # SETTINGS
        # =============================================

        self.min_delay = min_delay

        self.user_agent = user_agent

        self.respect_robots = respect_robots

        # =============================================
        # STATS
        # =============================================

        self.visited = set()

        self.blocked = 0

        self.failed = 0

        self.start_time = time.time()

        # =============================================
        # SEMAPHORE
        # =============================================

        self.semaphore = asyncio.Semaphore(
            max_concurrent
        )

    # =====================================================
    # SESSION
    # =====================================================

    async def _get_session(self):

        if not self.session:

            timeout = aiohttp.ClientTimeout(
                total=20
            )

            self.session = aiohttp.ClientSession(

                timeout=timeout,

                headers={
                    "User-Agent":
                        self.user_agent
                }
            )

        return self.session

    # =====================================================
    # FETCH
    # =====================================================

    async def fetch(
        self,
        url: str
    ) -> Optional[str]:
        """
        Загрузка HTML.
        """

        async with self.semaphore:

            domain = urlparse(url).netloc

            session = await self._get_session()

            # =========================================
            # ROBOTS.TXT
            # =========================================

            if self.respect_robots:

                parser = (
                    await self.robots.fetch_robots(
                        session,
                        url
                    )
                )

                if not parser.can_fetch(
                    self.user_agent,
                    url
                ):

                    print(
                        f"🚫 blocked by robots.txt: "
                        f"{url}"
                    )

                    self.blocked += 1

                    return None

            # =========================================
            # RATE LIMIT
            # =========================================

            await self.rate_limiter.acquire(
                domain
            )

            # =========================================
            # CRAWL DELAY
            # =========================================

            delay = (
                self.robots.get_crawl_delay(
                    domain,
                    self.user_agent
                )
            )

            if delay > 0:

                await asyncio.sleep(delay)

            # =========================================
            # JITTER
            # =========================================

            await asyncio.sleep(

                self.min_delay +

                random.uniform(0, 0.5)
            )

            # =========================================
            # REQUEST
            # =========================================

            try:

                async with session.get(
                    url
                ) as resp:

                    resp.raise_for_status()

                    return await resp.text()

            except Exception as e:

                print(
                    f"❌ Error: "
                    f"{url} | {e}"
                )

                self.failed += 1

                return None

    # =====================================================
    # WORKER
    # =====================================================

    async def worker(
        self,
        queue: asyncio.Queue,
        results: Dict[str, dict],
        max_pages: int
    ):
        """
        Worker обработки URL.

        ВАЖНО:
        НЕ используем queue.empty().
        """

        while True:

            # =========================================
            # WAIT NEXT TASK
            # =========================================

            url = await queue.get()

            # =========================================
            # POISON PILL
            # =========================================

            if url is None:

                queue.task_done()

                return

            try:

                # =====================================
                # FETCH
                # =====================================

                html = await self.fetch(url)

                if not html:
                    continue

                # =====================================
                # PARSE
                # =====================================

                data = self.parser.parse(
                    html,
                    url
                )

                results[url] = data

                # =====================================
                # NEW LINKS
                # =====================================

                for link in data["links"]:

                    if (
                        len(self.visited)
                        >= max_pages
                    ):
                        continue

                    if link not in self.visited:

                        self.visited.add(link)

                        await queue.put(link)

            finally:

                # =====================================
                # TASK DONE
                # =====================================

                queue.task_done()

    # =====================================================
    # CRAWL
    # =====================================================

    async def crawl(
        self,
        start_urls: List[str],
        max_pages=20
    ):
        """
        Главный crawler loop.
        """

        queue = asyncio.Queue()

        # =============================================
        # START URLS
        # =============================================

        for url in start_urls:

            await queue.put(url)

            self.visited.add(url)

        results = {}

        # =============================================
        # WORKERS
        # =============================================

        workers = [

            asyncio.create_task(

                self.worker(
                    queue,
                    results,
                    max_pages
                )

            )

            for _ in range(5)
        ]

        # =============================================
        # LIVE STATS
        # =============================================

        async def stats_monitor():

            while True:

                elapsed = (

                    time.time()

                    - self.start_time
                )

                rps = (

                    len(results) / elapsed

                    if elapsed > 0

                    else 0
                )

                print(

                    f"📊 "

                    f"pages={len(results)} "

                    f"blocked={self.blocked} "

                    f"failed={self.failed} "

                    f"speed={rps:.2f} req/sec"
                )

                await asyncio.sleep(1)

        monitor = asyncio.create_task(
            stats_monitor()
        )

        # =============================================
        # WAIT ALL TASKS
        # =============================================

        await queue.join()

        # =============================================
        # STOP WORKERS
        # =============================================

        for _ in workers:

            await queue.put(None)

        await asyncio.gather(*workers)

        monitor.cancel()

        return results

    # =====================================================
    # CLOSE
    # =====================================================

    async def close(self):
        """
        Закрытие session.
        """

        if self.session:

            await self.session.close()


# =========================================================
# DEMO
# =========================================================

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

            start_urls=[
                "https://httpbin.org/links/5/0"
            ],

            max_pages=10
        )

        print(
            f"\n✅ Итог: "
            f"{len(results)} страниц"
        )

    finally:

        await crawler.close()


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    asyncio.run(main())