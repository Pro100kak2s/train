import asyncio
import aiohttp
import time

from typing import Dict
from typing import List
from typing import Optional
from typing import Set

from urllib.parse import urlparse
from urllib.parse import urljoin

from bs4 import BeautifulSoup


# =========================================================
# QUEUE
# =========================================================

class CrawlerQueue:
    """
    Очередь crawler.

    Хранит:
    - URL для обработки
    - visited ссылки
    - ошибки
    - обработанные страницы
    """

    def __init__(self):

        # =============================================
        # PRIORITY QUEUE
        # =============================================

        # Формат:
        # (priority, depth, url)

        self.queue = asyncio.PriorityQueue()

        # =============================================
        # VISITED URLS
        # =============================================

        self.visited: Set[str] = set()

        # =============================================
        # FAILED URLS
        # =============================================

        self.failed: Dict[str, str] = {}

        # =============================================
        # PROCESSED DATA
        # =============================================

        self.processed: Dict[str, dict] = {}

    # =====================================================
    # ADD URL
    # =====================================================

    def add_url(
        self,
        url: str,
        priority: int = 0,
        depth: int = 0
    ):
        """
        Добавление URL в очередь.
        """

        # =============================================
        # SKIP DUPLICATES
        # =============================================

        if url in self.visited:
            return

        # =============================================
        # MARK VISITED
        # =============================================

        self.visited.add(url)

        # =============================================
        # ADD TO QUEUE
        # =============================================

        self.queue.put_nowait(
            (priority, depth, url)
        )

    # =====================================================
    # GET NEXT ITEM
    # =====================================================

    async def get_next_item(self):
        """
        Получение следующего элемента.

        ВАЖНО:
        НЕ используем queue.empty()
        чтобы избежать race condition.
        """

        return await self.queue.get()

    # =====================================================
    # TASK DONE
    # =====================================================

    def task_done(self):
        """
        Сообщаем queue,
        что задача завершена.
        """

        self.queue.task_done()

    # =====================================================
    # WAIT ALL TASKS
    # =====================================================

    async def join(self):
        """
        Ждём завершения всех задач.
        """

        await self.queue.join()

    # =====================================================
    # MARK PROCESSED
    # =====================================================

    def mark_processed(
        self,
        url: str,
        data: dict
    ):
        """
        Помечаем URL как успешно обработанный.
        """

        self.processed[url] = data

    # =====================================================
    # MARK FAILED
    # =====================================================

    def mark_failed(
        self,
        url: str,
        error: str
    ):
        """
        Сохраняем ошибку.
        """

        self.failed[url] = error

    # =====================================================
    # STATS
    # =====================================================

    def get_stats(self):
        """
        Статистика crawler.
        """

        return {

            "queue_size":
                self.queue.qsize(),

            "processed":
                len(self.processed),

            "failed":
                len(self.failed),

            "visited":
                len(self.visited),
        }


# =========================================================
# SEMAPHORE MANAGER
# =========================================================

class SemaphoreManager:
    """
    Ограничение параллелизма.

    Поддерживает:
    - global limit
    - per-domain limit
    """

    def __init__(
        self,
        global_limit: int = 10,
        per_domain_limit: int = 3
    ):

        # =============================================
        # GLOBAL LIMIT
        # =============================================

        self.global_semaphore = asyncio.Semaphore(
            global_limit
        )

        # =============================================
        # PER DOMAIN LIMIT
        # =============================================

        self.per_domain_limit = per_domain_limit

        # =============================================
        # DOMAIN SEMAPHORES
        # =============================================

        self.domain_semaphores = {}

    # =====================================================
    # GET DOMAIN
    # =====================================================

    def _get_domain(
        self,
        url: str
    ):

        return urlparse(url).netloc

    # =====================================================
    # GET DOMAIN SEMAPHORE
    # =====================================================

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

    # =====================================================
    # ACQUIRE
    # =====================================================

    async def acquire(
        self,
        url: str
    ):
        """
        Захватываем:
        - global semaphore
        - domain semaphore
        """

        domain = self._get_domain(url)

        domain_sem = (
            self._get_domain_semaphore(domain)
        )

        await self.global_semaphore.acquire()

        await domain_sem.acquire()

        return domain_sem

    # =====================================================
    # RELEASE
    # =====================================================

    def release(
        self,
        domain_sem
    ):
        """
        Освобождаем semaphore.
        """

        domain_sem.release()

        self.global_semaphore.release()


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

        # =============================================
        # PARSE HTML
        # =============================================

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
    Асинхронный crawler.
    """

    def __init__(
        self,
        max_concurrent=10,
        max_depth=2
    ):

        # =============================================
        # SESSION
        # =============================================

        self.session = None

        # =============================================
        # QUEUE
        # =============================================

        self.queue = CrawlerQueue()

        # =============================================
        # SEMAPHORE
        # =============================================

        self.sem = SemaphoreManager(
            global_limit=max_concurrent
        )

        # =============================================
        # PARSER
        # =============================================

        self.parser = HTMLParser()

        # =============================================
        # MAX DEPTH
        # =============================================

        self.max_depth = max_depth

    # =====================================================
    # SESSION
    # =====================================================

    async def _get_session(self):

        if not self.session:

            timeout = aiohttp.ClientTimeout(
                total=20
            )

            self.session = aiohttp.ClientSession(
                timeout=timeout
            )

        return self.session

    # =====================================================
    # FILTERS
    # =====================================================

    def _should_visit(
        self,
        url: str,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> bool:
        """
        Проверка URL фильтров.
        """

        # =============================================
        # EXCLUDE
        # =============================================

        if exclude_patterns:

            for pattern in exclude_patterns:

                if pattern in url:
                    return False

        # =============================================
        # INCLUDE
        # =============================================

        if include_patterns:

            return any(

                pattern in url

                for pattern in include_patterns
            )

        return True

    # =====================================================
    # FETCH
    # =====================================================

    async def fetch(
        self,
        url: str
    ) -> Optional[str]:
        """
        HTTP request.
        """

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

    # =====================================================
    # WORKER
    # =====================================================

    async def worker(
        self,
        max_pages: int,
        same_domain_only: bool,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ):
        """
        Worker обработки URL.
        """

        while True:

            # =========================================
            # WAIT NEXT TASK
            # =========================================

            item = await self.queue.get_next_item()

            priority, depth, url = item

            # =========================================
            # POISON PILL
            # =========================================

            if url is None:

                self.queue.task_done()

                return

            try:

                # =====================================
                # MAX PAGES
                # =====================================

                if (
                    len(self.queue.processed)
                    >= max_pages
                ):
                    continue

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

                self.queue.mark_processed(
                    url,
                    data
                )

                # =====================================
                # MAX DEPTH
                # =====================================

                if depth >= self.max_depth:
                    continue

                # =====================================
                # NEW LINKS
                # =====================================

                for link in data["links"]:

                    # ================================
                    # SAME DOMAIN FILTER
                    # ================================

                    if same_domain_only:

                        if (

                            urlparse(link).netloc

                            !=

                            urlparse(url).netloc
                        ):
                            continue

                    # ================================
                    # INCLUDE/EXCLUDE FILTERS
                    # ================================

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

            finally:

                # =====================================
                # TASK DONE
                # =====================================

                self.queue.task_done()

    # =====================================================
    # CRAWL
    # =====================================================

    async def crawl(
        self,
        start_urls: List[str],
        max_pages: int = 50,
        same_domain_only: bool = True,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ):
        """
        Главный метод crawler.
        """

        # =============================================
        # ADD START URLS
        # =============================================

        for url in start_urls:

            self.queue.add_url(
                url,
                priority=0,
                depth=0
            )

        # =============================================
        # CREATE WORKERS
        # =============================================

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

        # =============================================
        # STATS MONITOR
        # =============================================

        async def stats_monitor():

            while True:

                stats = self.queue.get_stats()

                print(

                    f"📊 "

                    f"processed={stats['processed']} "

                    f"queue={stats['queue_size']} "

                    f"failed={stats['failed']}"
                )

                await asyncio.sleep(1)

        monitor = asyncio.create_task(
            stats_monitor()
        )

        # =============================================
        # WAIT ALL TASKS
        # =============================================

        await self.queue.join()

        # =============================================
        # STOP WORKERS
        # =============================================

        for _ in workers:

            self.queue.queue.put_nowait(
                (
                    float("inf"),
                    float("inf"),
                    None
                )
            )

        await asyncio.gather(*workers)

        monitor.cancel()

        end = time.time()

        print(
            f"\n⏱️ {end - start:.2f} sec"
        )

        return self.queue.processed

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
        max_concurrent=10,
        max_depth=2
    )

    try:

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