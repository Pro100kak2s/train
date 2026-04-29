import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

# Используем HTMLParser из Day 2
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# ==========================================
# QUEUE (с приоритетом)
# ==========================================

class CrawlerQueue:
    def __init__(self):
        self.queue = asyncio.PriorityQueue()
        self.visited: Set[str] = set()
        self.failed: Dict[str, str] = {}
        self.processed: Dict[str, dict] = {}

    def add_url(self, url: str, priority: int = 0, depth: int = 0):
        if url in self.visited:
            return
        self.queue.put_nowait((priority, depth, url))
        self.visited.add(url)

    async def get_next(self) -> Optional[Tuple[int, int, str]]:
        if self.queue.empty():
            return None
        return await self.queue.get()

    def mark_processed(self, url: str, data: dict):
        self.processed[url] = data

    def mark_failed(self, url: str, error: str):
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
    def __init__(self, global_limit: int = 10, per_domain_limit: int = 3):
        self.global_semaphore = asyncio.Semaphore(global_limit)
        self.domain_semaphores: Dict[str, asyncio.Semaphore] = {}
        self.per_domain_limit = per_domain_limit

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc

    def _get_domain_semaphore(self, domain: str):
        if domain not in self.domain_semaphores:
            self.domain_semaphores[domain] = asyncio.Semaphore(self.per_domain_limit)
        return self.domain_semaphores[domain]

    async def acquire(self, url: str):
        domain = self._get_domain(url)
        domain_sem = self._get_domain_semaphore(domain)

        await self.global_semaphore.acquire()
        await domain_sem.acquire()

        return domain_sem

    def release(self, domain_sem):
        domain_sem.release()
        self.global_semaphore.release()


# ==========================================
# HTML PARSER (упрощённый)
# ==========================================

class HTMLParser:
    def parse(self, html: str, base_url: str) -> dict:
        soup = BeautifulSoup(html, "lxml")

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
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
    def __init__(self, max_concurrent=10, max_depth=2):
        self.session: Optional[aiohttp.ClientSession] = None
        self.queue = CrawlerQueue()
        self.sem = SemaphoreManager(global_limit=max_concurrent)
        self.parser = HTMLParser()
        self.max_depth = max_depth

    async def _get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch(self, url: str) -> Optional[str]:
        domain_sem = await self.sem.acquire(url)

        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.text()
        except Exception as e:
            return None
        finally:
            self.sem.release(domain_sem)

    async def worker(self, max_pages: int, same_domain_only: bool):
        while True:
            if len(self.queue.processed) >= max_pages:
                return

            item = await self.queue.get_next()
            if not item:
                return

            priority, depth, url = item

            html = await self.fetch(url)

            if not html:
                self.queue.mark_failed(url, "fetch error")
                continue

            data = self.parser.parse(html, url)
            self.queue.mark_processed(url, data)

            # добавляем новые ссылки
            if depth < self.max_depth:
                for link in data["links"]:
                    if same_domain_only:
                        if urlparse(link).netloc != urlparse(url).netloc:
                            continue

                    self.queue.add_url(link, priority=depth + 1, depth=depth + 1)

    async def crawl(
        self,
        start_urls: List[str],
        max_pages: int = 50,
        same_domain_only: bool = True,
    ) -> Dict[str, dict]:

        for url in start_urls:
            self.queue.add_url(url, priority=0, depth=0)

        workers = [
            asyncio.create_task(self.worker(max_pages, same_domain_only))
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
    crawler = AsyncCrawler(max_concurrent=10, max_depth=2)

    results = await crawler.crawl(
        start_urls=["https://httpbin.org/links/5/0"],
        max_pages=20,
        same_domain_only=True
    )

    print(f"\n✅ Итог: {len(results)} страниц")

    await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())