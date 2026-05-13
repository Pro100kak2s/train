import asyncio
import aiohttp
import aiofiles

import argparse
import json
import logging
import time

import xml.etree.ElementTree as ET

from logging.handlers import RotatingFileHandler

from collections import Counter

from datetime import datetime

from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from urllib.parse import urlparse
from urllib.parse import urljoin

from bs4 import BeautifulSoup


# =========================================================
# CONFIG
# =========================================================

DEFAULT_CONFIG = {

    "max_concurrent": 10,

    "max_pages": 100,

    "max_depth": 2,

    "rate_limit": 0.5,

    "respect_robots": True,

    "start_urls": [
        "https://example.com"
    ],

    "output_file": "results.json",

    "log_file": "crawler.log"
}


# =========================================================
# LOGGER
# =========================================================

class LoggerManager:

    @staticmethod
    def setup_logger(
        log_file: str
    ):

        logger = logging.getLogger(
            "AdvancedCrawler"
        )

        # =============================================
        # AVOID DUPLICATE HANDLERS
        # =============================================

        if logger.handlers:
            return logger

        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(

            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        )

        # =============================================
        # FILE HANDLER
        # =============================================

        file_handler = RotatingFileHandler(

            log_file,

            maxBytes=1024 * 1024,

            backupCount=3
        )

        file_handler.setFormatter(
            formatter
        )

        # =============================================
        # CONSOLE HANDLER
        # =============================================

        console_handler = logging.StreamHandler()

        console_handler.setFormatter(
            formatter
        )

        logger.addHandler(file_handler)

        logger.addHandler(console_handler)

        return logger


# =========================================================
# STORAGE
# =========================================================

class JSONStorage:

    def __init__(
        self,
        filename: str
    ):

        self.filename = filename

        self.lock = asyncio.Lock()

        self.saved = 0

    # =====================================================
    # SAVE
    # =====================================================

    async def save(
        self,
        data: dict
    ):

        async with self.lock:

            try:

                async with aiofiles.open(
                    self.filename,
                    mode="a",
                    encoding="utf-8"
                ) as f:

                    line = json.dumps(
                        data,
                        ensure_ascii=False
                    )

                    await f.write(
                        line + "\n"
                    )

                    self.saved += 1

            except Exception as e:

                print(
                    f"❌ Save error: {e}"
                )

    # =====================================================
    # CLOSE
    # =====================================================

    async def close(self):

        print(
            f"✅ Saved: {self.saved}"
        )


# =========================================================
# STATS
# =========================================================

class CrawlerStats:

    def __init__(self):

        self.start_time = time.time()

        self.total_pages = 0

        self.successful = 0

        self.failed = 0

        self.status_codes = Counter()

        self.domains = Counter()

    # =====================================================
    # SUCCESS
    # =====================================================

    def add_success(
        self,
        url: str,
        status_code: int
    ):

        self.total_pages += 1

        self.successful += 1

        self.status_codes[
            status_code
        ] += 1

        domain = urlparse(url).netloc

        self.domains[domain] += 1

    # =====================================================
    # FAILED
    # =====================================================

    def add_failed(self):

        self.failed += 1

    # =====================================================
    # SPEED
    # =====================================================

    def get_speed(self):

        elapsed = (
            time.time()
            - self.start_time
        )

        if elapsed == 0:
            return 0

        return self.total_pages / elapsed

    # =====================================================
    # REPORT
    # =====================================================

    def get_report(self):

        elapsed = (
            time.time()
            - self.start_time
        )

        return {

            "total_pages":
                self.total_pages,

            "successful":
                self.successful,

            "failed":
                self.failed,

            "speed":
                round(
                    self.get_speed(),
                    2
                ),

            "status_codes":
                dict(self.status_codes),

            "top_domains":
                dict(
                    self.domains.most_common(10)
                ),

            "elapsed":
                round(elapsed, 2)
        }


# =========================================================
# SITEMAP PARSER
# =========================================================

class SitemapParser:

    async def fetch_sitemap(
        self,
        sitemap_url: str
    ) -> List[str]:

        urls = []

        try:

            timeout = aiohttp.ClientTimeout(
                total=20
            )

            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                async with session.get(
                    sitemap_url
                ) as resp:

                    if resp.status != 200:
                        return []

                    xml = await resp.text()

            root = ET.fromstring(xml)

            namespace = {

                "ns":
                    "http://www.sitemaps.org/schemas/sitemap/0.9"
            }

            # =========================================
            # SITEMAP INDEX
            # =========================================

            sitemap_tags = root.findall(
                ".//ns:sitemap/ns:loc",
                namespace
            )

            if sitemap_tags:

                for tag in sitemap_tags:

                    nested_urls = (
                        await self.fetch_sitemap(
                            tag.text
                        )
                    )

                    urls.extend(
                        nested_urls
                    )

            # =========================================
            # URLSET
            # =========================================

            url_tags = root.findall(
                ".//ns:url/ns:loc",
                namespace
            )

            for tag in url_tags:

                urls.append(
                    tag.text
                )

        except Exception as e:

            print(
                f"❌ Sitemap error: {e}"
            )

        return urls


# =========================================================
# HTML PARSER
# =========================================================

class HTMLParser:

    def parse(
        self,
        html: str,
        url: str
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
        # TEXT
        # =============================================

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        # =============================================
        # LINKS
        # =============================================

        links = [

            urljoin(
                url,
                a.get("href")
            )

            for a in soup.find_all(
                "a",
                href=True
            )
        ]

        return {

            "url": url,

            "title": title,

            "text": text,

            "links": list(set(links)),

            "crawled_at": str(
                datetime.utcnow()
            )
        }


# =========================================================
# ADVANCED CRAWLER
# =========================================================

class AdvancedCrawler:

    def __init__(
        self,
        config: dict
    ):

        self.config = config

        self.storage = JSONStorage(
            config["output_file"]
        )

        self.stats = CrawlerStats()

        self.logger = (
            LoggerManager.setup_logger(
                config["log_file"]
            )
        )

        self.sitemap_parser = SitemapParser()

        self.parser = HTMLParser()

        self.session = None

        self.visited: Set[str] = set()

        self.queue = asyncio.Queue()

        self.semaphore = asyncio.Semaphore(
            config["max_concurrent"]
        )

    # =====================================================
    # FROM CONFIG
    # =====================================================

    @classmethod
    def from_config(
        cls,
        filename: str
    ):

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            config = json.load(f)

        return cls(config)

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
    # FETCH
    # =====================================================

    async def fetch(
        self,
        url: str
    ) -> Optional[str]:

        async with self.semaphore:

            try:

                session = await self._get_session()

                async with session.get(url) as resp:

                    resp.raise_for_status()

                    html = await resp.text()

                    self.stats.add_success(
                        url,
                        resp.status
                    )

                    self.logger.info(
                        f"SUCCESS {url}"
                    )

                    return html

            except Exception as e:

                self.stats.add_failed()

                self.logger.error(
                    f"ERROR {url} | {e}"
                )

                return None

    # =====================================================
    # PROCESS URL
    # =====================================================

    async def process_url(
        self,
        url: str,
        depth: int
    ):

        # =============================================
        # VALIDATION
        # =============================================

        if depth > self.config["max_depth"]:
            return

        if len(self.visited) >= self.config["max_pages"]:
            return

        # =============================================
        # FETCH
        # =============================================

        html = await self.fetch(url)

        if not html:
            return

        # =============================================
        # PARSE
        # =============================================

        data = self.parser.parse(
            html,
            url
        )

        # =============================================
        # SAVE
        # =============================================

        await self.storage.save(data)

        # =============================================
        # NEW LINKS
        # =============================================

        for link in data["links"]:

            # =========================================
            # MAX PAGES LIMIT
            # =========================================

            if len(self.visited) >= self.config["max_pages"]:
                break

            # =========================================
            # SKIP DUPLICATES
            # =========================================

            if link in self.visited:
                continue

            # =========================================
            # RESERVE URL IMMEDIATELY
            # =========================================

            self.visited.add(link)

            await self.queue.put(
                (
                    link,
                    depth + 1
                )
            )

    # =====================================================
    # WORKER
    # =====================================================

    async def worker(self):

        while True:

            item = await self.queue.get()

            try:

                # =====================================
                # POISON PILL
                # =====================================

                if item is None:
                    return

                url, depth = item

                await self.process_url(
                    url,
                    depth
                )

            except Exception as e:

                self.logger.error(
                    f"Worker error: {e}"
                )

            finally:

                self.queue.task_done()

    # =====================================================
    # MONITOR
    # =====================================================

    async def monitor(self):

        while True:

            report = (
                self.stats.get_report()
            )

            print(

                f"📊 "

                f"pages={report['total_pages']} "

                f"success={report['successful']} "

                f"failed={report['failed']} "

                f"speed={report['speed']} p/s "

                f"queue={self.queue.qsize()}"
            )

            await asyncio.sleep(2)

    # =====================================================
    # CRAWL
    # =====================================================

    async def crawl(self):

        # =============================================
        # START URLS
        # =============================================

        for url in self.config["start_urls"]:

            self.visited.add(url)

            await self.queue.put(
                (
                    url,
                    0
                )
            )

        # =============================================
        # SITEMAP SUPPORT
        # =============================================

        for url in self.config["start_urls"]:

            parsed = urlparse(url)

            sitemap_url = (

                f"{parsed.scheme}://"

                f"{parsed.netloc}/sitemap.xml"
            )

            sitemap_urls = (
                await self.sitemap_parser
                .fetch_sitemap(
                    sitemap_url
                )
            )

            for sitemap_link in sitemap_urls:

                if (
                    len(self.visited)
                    >=
                    self.config["max_pages"]
                ):
                    break

                if sitemap_link in self.visited:
                    continue

                self.visited.add(
                    sitemap_link
                )

                await self.queue.put(
                    (
                        sitemap_link,
                        0
                    )
                )

        # =============================================
        # WORKERS
        # =============================================

        workers = [

            asyncio.create_task(
                self.worker()
            )

            for _ in range(
                self.config[
                    "max_concurrent"
                ]
            )
        ]

        # =============================================
        # MONITOR
        # =============================================

        monitor_task = (
            asyncio.create_task(
                self.monitor()
            )
        )

        # =============================================
        # WAIT ALL TASKS
        # =============================================

        await self.queue.join()

        # =============================================
        # STOP WORKERS
        # =============================================

        for _ in workers:

            await self.queue.put(None)

        # =============================================
        # WAIT WORKERS FINISH
        # =============================================

        await asyncio.gather(
            *workers,
            return_exceptions=True
        )

        # =============================================
        # STOP MONITOR
        # =============================================

        monitor_task.cancel()

        try:

            await monitor_task

        except asyncio.CancelledError:

            pass

    # =====================================================
    # EXPORT JSON
    # =====================================================

    def export_to_json(
        self,
        filename: str
    ):

        report = (
            self.stats.get_report()
        )

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(

                report,

                f,

                indent=2,

                ensure_ascii=False
            )

    # =====================================================
    # EXPORT HTML
    # =====================================================

    def export_to_html_report(
        self,
        filename: str
    ):

        report = (
            self.stats.get_report()
        )

        html = f"""

        <html>

        <head>

            <title>Crawler Report</title>

        </head>

        <body>

            <h1>Crawler Report</h1>

            <p>
                Total pages:
                {report['total_pages']}
            </p>

            <p>
                Successful:
                {report['successful']}
            </p>

            <p>
                Failed:
                {report['failed']}
            </p>

            <p>
                Speed:
                {report['speed']} p/s
            </p>

            <h2>Status Codes</h2>

            <pre>
{json.dumps(report['status_codes'], indent=2)}
            </pre>

            <h2>Top Domains</h2>

            <pre>
{json.dumps(report['top_domains'], indent=2)}
            </pre>

        </body>

        </html>

        """

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(html)

    # =====================================================
    # GET STATS
    # =====================================================

    def get_stats(self):

        return self.stats.get_report()

    # =====================================================
    # CLOSE
    # =====================================================

    async def close(self):

        if self.session:

            await self.session.close()

        await self.storage.close()


# =========================================================
# CONFIG FILE
# =========================================================

def create_default_config():

    with open(
        "config.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(

            DEFAULT_CONFIG,

            f,

            indent=2,

            ensure_ascii=False
        )


# =========================================================
# MAIN
# =========================================================

async def async_main(args):

    # =============================================
    # CONFIG
    # =============================================

    if args.config:

        crawler = (
            AdvancedCrawler
            .from_config(
                args.config
            )
        )

    else:

        config = DEFAULT_CONFIG.copy()

        # =========================================
        # CLI OVERRIDES
        # =========================================

        if args.urls:

            config["start_urls"] = (
                args.urls
            )

        if args.max_pages:

            config["max_pages"] = (
                args.max_pages
            )

        if args.max_depth:

            config["max_depth"] = (
                args.max_depth
            )

        if args.output:

            config["output_file"] = (
                args.output
            )

        crawler = AdvancedCrawler(
            config
        )

    # =============================================
    # RUN
    # =============================================

    try:

        await crawler.crawl()

        stats = crawler.get_stats()

        print("\n✅ FINAL STATS")

        print(

            json.dumps(

                stats,

                indent=2,

                ensure_ascii=False
            )
        )

        # =========================================
        # EXPORT
        # =========================================

        crawler.export_to_json(
            "stats.json"
        )

        crawler.export_to_html_report(
            "report.html"
        )

    finally:

        # =========================================
        # GRACEFUL CLOSE
        # =========================================

        await crawler.close()


# =========================================================
# CLI
# =========================================================

def parse_args():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--urls",
        nargs="+"
    )

    parser.add_argument(
        "--max-pages",
        type=int
    )

    parser.add_argument(
        "--max-depth",
        type=int
    )

    parser.add_argument(
        "--output"
    )

    parser.add_argument(
        "--config"
    )

    return parser.parse_args()


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    create_default_config()

    args = parse_args()

    asyncio.run(
        async_main(args)
    )