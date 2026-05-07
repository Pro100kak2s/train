import asyncio
import aiohttp
import time

from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup


# ==========================================
# QUEUE
# ==========================================

class CrawlerQueue:
    def __init__(self):

        self.queue = asyncio.PriorityQueue()

        self.visited: Set[str] = set()

        self.failed: Dict[str, str] = {}

        self.processed: Dict[str, dict] = {}

    def add_url(
        self,
        url: str,
        priority: int = 0,
        depth: int = 0
    ):

        if url in self.visited:
            return

        self.queue.put_nowait(
            (priority, depth, url)
        )

        self.visited.add(url)

    # ==========================================
    # INTERNAL API
    # ==========================================

    async def get_next_item(
        self
    ) -> Optional[Tuple[int, int, str]]:

        if self.queue.empty():
            return None

        return await self.queue.get()

    # ==========================================
    # PUBLIC API
    # ==========================================

    async def get_next(self) -> Optional[str]:

        item = await self.get_next_item()

        if not item:
            return None

        _, _, url = item

        return url

    def mark_processed(
        self,
        url: str,
        data: dict
    ):

        self.processed[url] = data

    def mark_failed(
        self,
        url: str,
        error: str
    ):

        self.failed[url] = error

    def get_stats(self):

        return {
            "queue_size": self.queue.qsize(),
            "processed": len(self.processed),
            "failed": len(self.failed),
            "visited": len(self.visited),
        }


# ==========================================
# SEMAPHORE MANAGER
# ==========================================

class SemaphoreManager:
    def __init__(
        self,
        global_limit: int = 10,
        per_domain_limit: int = 3
    ):

        self.global_semaphore = asyncio.Semaphore(
            global_limit
        )

        self.per_domain_limit = per_domain_limit

        self.domain_semaphores = {}

    def _get_domain(self, url: str):

        return urlparse(url).netloc

    def _get_domain_semaphore(
        self,
        domain: str
    ):

        if domain not in self.domain_semaphores:

            self.domain_semaphores[domain] = (
                asyncio.Semaphore(
                    self.per_domain_limit
                )
            )

        return self.domain_semaphores[domain]

    async def acquire(self, url: str):

        domain = self._get_domain(url)

        domain_sem = self._get_domain_semaphore(
            domain
        )

        await self.global_semaphore.acquire()

        await domain_sem.acquire()

        return domain_sem

    def release(self, domain_sem):

        domain_sem.release()

        self.global_semaphore.release()


# ==========================================
# HTML PARSER
# ==========================================

class HTMLParser:
    def parse(
        self,
        html: str,
        base_url: str
    ) -> dict:

        soup = BeautifulSoup(html, "lxml")

        title = (
            soup.title.string.strip()
            if soup.title and soup.title.string
            else ""
        )

        links = [

            urljoin(base_url, a.get("href"))

            for a in soup.find_all("a", href=True)
        ]

        return {
            "title": title,
            "links": list(set(links))
        }


# ==========================================
# ASYNC CRAWLER
# ==========================================

class AsyncCrawler:
    def __init__(
        self,
        max_concurrent=10,
        max_depth=2
    ):

        self.session = None

        self.queue = CrawlerQueue()

        self.sem = SemaphoreManager(
            global_limit=max_concurrent
        )

        self.parser = HTMLParser()

        self.max_depth = max_depth

    async def _get_session(self):

        if not self.session:

            timeout = aiohttp.ClientTimeout(
                total=20
            )

            self.session = aiohttp.ClientSession(
                timeout=timeout
            )

        return self.session

    # ==========================================
    # FILTERS
    # ==========================================

    def _should_visit(
        self,
        url: str,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> bool:

        if exclude_patterns:

            for pattern in exclude_patterns:

                if pattern in url:
                    return False

        if include_patterns:

            return any(
                pattern in url
                for pattern in include_patterns
            )

        return True

    async def fetch(
        self,
        url: str
    ) -> Optional[str]:

        domain_sem = await self.sem.acquire(url)

        try:

            session = await self._get_session()

            async with session.get(url) as resp:

                resp.raise_for_status()

                return await resp.text()

        except Exception as e:

            self.queue.mark_failed(
                url,
                str(e)
            )

            return None

        finally:

            self.sem.release(domain_sem)

    async def worker(
        self,
        max_pages: int,
        same_domain_only: bool,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ):

        while True:

            if len(self.queue.processed) >= max_pages:
                return

            item = await self.queue.get_next_item()

            if not item:
                return

            priority, depth, url = item

            html = await self.fetch(url)

            if not html:
                continue

            data = self.parser.parse(html, url)

            self.queue.mark_processed(url, data)

            if depth >= self.max_depth:
                continue

            for link in data["links"]:

                # same domain filter

                if same_domain_only:

                    if (
                        urlparse(link).netloc
                        != urlparse(url).netloc
                    ):
                        continue

                # include/exclude filter

                if not self._should_visit(
                    link,
                    include_patterns,
                    exclude_patterns
                ):
                    continue

                self.queue.add_url(
                    link,
                    priority=depth + 1,
                    depth=depth + 1
                )

    async def crawl(
        self,
        start_urls: List[str],
        max_pages: int = 50,
        same_domain_only: bool = True,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ):

        for url in start_urls:

            self.queue.add_url(
                url,
                priority=0,
                depth=0
            )

        workers = [

            asyncio.create_task(
                self.worker(
                    max_pages,
                    same_domain_only,
                    include_patterns,
                    exclude_patterns
                )
            )

            for _ in range(5)
        ]

        start = time.time()

        while any(not w.done() for w in workers):

            stats = self.queue.get_stats()

            print(
                f"📊 processed={stats['processed']} "
                f"queue={stats['queue_size']} "
                f"failed={stats['failed']}"
            )

            await asyncio.sleep(1)

        await asyncio.gather(*workers)

        end = time.time()

        print(f"⏱️ {end - start:.2f} sec")

        return self.queue.processed

    async def close(self):

        if self.session:
            await self.session.close()


# ==========================================
# DEMO
# ==========================================

async def main():

    crawler = AsyncCrawler(
        max_concurrent=10,
        max_depth=2
    )

    results = await crawler.crawl(

        start_urls=[
            "https://httpbin.org/links/5/0"
        ],

        max_pages=20,

        same_domain_only=True,

        include_patterns=[
            "httpbin"
        ],

        exclude_patterns=[
            "image",
            "css",
            "js"
        ]
    )

    print(f"\n✅ Итог: {len(results)} страниц")

    await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())