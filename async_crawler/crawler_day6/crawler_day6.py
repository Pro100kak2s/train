import asyncio
import aiohttp
import aiofiles
import aiosqlite

import csv
import json
import time

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from bs4 import BeautifulSoup


# =========================================================
# BASE STORAGE
# =========================================================

class DataStorage(ABC):
    """
    Абстрактное хранилище данных
    """

    @abstractmethod
    async def save(self, data: dict):
        pass

    @abstractmethod
    async def close(self):
        pass


# =========================================================
# JSON STORAGE
# =========================================================

class JSONStorage(DataStorage):
    """
    Асинхронное сохранение в JSON
    """

    def __init__(
        self,
        filename: str,
        pretty: bool = True
    ):

        self.filename = filename

        self.pretty = pretty

        self.lock = asyncio.Lock()

        self.items_saved = 0

    async def save(self, data: dict):

        async with self.lock:

            try:

                async with aiofiles.open(
                    self.filename,
                    mode="a",
                    encoding="utf-8"
                ) as f:

                    json_line = json.dumps(
                        data,
                        ensure_ascii=False
                    )

                    await f.write(json_line + "\n")

                    self.items_saved += 1

            except Exception as e:

                print(
                    f"❌ JSON save error: {e}"
                )

    async def close(self):

        print(
            f"✅ JSON saved: "
            f"{self.items_saved}"
        )


# =========================================================
# CSV STORAGE
# =========================================================

class CSVStorage(DataStorage):
    """
    Асинхронное сохранение CSV
    """

    def __init__(
        self,
        filename: str,
        encoding: str = "utf-8"
    ):

        self.filename = filename

        self.encoding = encoding

        self.headers_written = False

        self.lock = asyncio.Lock()

        self.items_saved = 0

    async def save(self, data: dict):

        async with self.lock:

            try:

                # =====================================
                # HEADERS
                # =====================================

                if not self.headers_written:

                    async with aiofiles.open(
                        self.filename,
                        mode="w",
                        encoding=self.encoding
                    ) as f:

                        headers = ",".join(
                            data.keys()
                        )

                        await f.write(
                            headers + "\n"
                        )

                    self.headers_written = True

                # =====================================
                # VALUES
                # =====================================

                values = []

                for value in data.values():

                    if isinstance(value, (dict, list)):

                        value = json.dumps(
                            value,
                            ensure_ascii=False
                        )

                    value = str(value).replace(
                        "\n",
                        " "
                    )

                    values.append(
                        f'"{value}"'
                    )

                row = ",".join(values)

                async with aiofiles.open(
                    self.filename,
                    mode="a",
                    encoding=self.encoding
                ) as f:

                    await f.write(row + "\n")

                self.items_saved += 1

            except Exception as e:

                print(
                    f"❌ CSV save error: {e}"
                )

    async def close(self):

        print(
            f"✅ CSV saved: "
            f"{self.items_saved}"
        )


# =========================================================
# SQLITE STORAGE
# =========================================================

class SQLiteStorage(DataStorage):
    """
    Асинхронное SQLite хранилище
    """

    def __init__(
        self,
        db_path: str
    ):

        self.db_path = db_path

        self.db = None

        self.items_saved = 0

        self.batch = []

        self.batch_size = 5

    # =====================================================
    # INIT DB
    # =====================================================

    async def init_db(self):

        self.db = await aiosqlite.connect(
            self.db_path
        )

        await self.db.execute("""

            CREATE TABLE IF NOT EXISTS pages (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                url TEXT,
                title TEXT,
                text TEXT,

                links TEXT,
                metadata TEXT,

                crawled_at TEXT,

                status_code INTEGER,

                content_type TEXT
            )

        """)

        # =============================================
        # INDEX
        # =============================================

        await self.db.execute("""

            CREATE INDEX IF NOT EXISTS
            idx_url
            ON pages(url)

        """)

        await self.db.commit()

    # =====================================================
    # SAVE
    # =====================================================

    async def save(self, data: dict):

        try:

            self.batch.append(data)

            # =========================================
            # BATCH INSERT
            # =========================================

            if len(self.batch) >= self.batch_size:

                await self.flush()

        except Exception as e:

            print(
                f"❌ SQLite save error: {e}"
            )

    # =====================================================
    # FLUSH
    # =====================================================

    async def flush(self):

        if not self.batch:
            return

        query = """

            INSERT INTO pages (

                url,
                title,
                text,

                links,
                metadata,

                crawled_at,

                status_code,

                content_type

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

        """

        values = []

        for item in self.batch:

            values.append(

                (

                    item.get("url"),

                    item.get("title"),

                    item.get("text"),

                    json.dumps(
                        item.get("links", [])
                    ),

                    json.dumps(
                        item.get("metadata", {})
                    ),

                    item.get("crawled_at"),

                    item.get("status_code"),

                    item.get("content_type"),
                )
            )

        await self.db.executemany(
            query,
            values
        )

        await self.db.commit()

        self.items_saved += len(self.batch)

        self.batch.clear()

    # =====================================================
    # READ DATA
    # =====================================================

    async def read_all(self):

        cursor = await self.db.execute(
            "SELECT * FROM pages"
        )

        rows = await cursor.fetchall()

        return rows

    # =====================================================
    # CLOSE
    # =====================================================

    async def close(self):

        await self.flush()

        if self.db:

            await self.db.close()

        print(
            f"✅ SQLite saved: "
            f"{self.items_saved}"
        )


# =========================================================
# HTML PARSER
# =========================================================

class HTMLParser:
    """
    HTML parser
    """

    def parse(
        self,
        html: str,
        url: str,
        status_code: int,
        content_type: str
    ) -> dict:

        try:

            soup = BeautifulSoup(
                html,
                "lxml"
            )

            title = (
                soup.title.string.strip()
                if soup.title and soup.title.string
                else ""
            )

            text = soup.get_text(
                separator=" ",
                strip=True
            )

            links = [

                a.get("href")

                for a in soup.find_all(
                    "a",
                    href=True
                )
            ]

            metadata = {}

            for meta in soup.find_all("meta"):

                name = (
                    meta.get("name")
                    or
                    meta.get("property")
                )

                content = meta.get("content")

                if name and content:

                    metadata[name] = content

            return {

                "url": url,

                "title": title,

                "text": text,

                "links": links,

                "metadata": metadata,

                "crawled_at": str(
                    datetime.utcnow()
                ),

                "status_code": status_code,

                "content_type": content_type
            }

        except Exception as e:

            print(
                f"❌ Parse error: {e}"
            )

            return {
                "url": url,
                "error": str(e)
            }


# =========================================================
# ASYNC CRAWLER
# =========================================================

class AsyncCrawler:
    """
    Async crawler with storage
    """

    def __init__(
        self,
        storage: DataStorage,
        max_concurrent: int = 5
    ):

        self.storage = storage

        self.semaphore = asyncio.Semaphore(
            max_concurrent
        )

        self.session = None

        self.parser = HTMLParser()

        self.saved_count = 0

        self.failed_count = 0

    # =====================================================
    # SESSION
    # =====================================================

    async def _get_session(self):

        if not self.session:

            timeout = aiohttp.ClientTimeout(
                total=15
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
    ):

        async with self.semaphore:

            try:

                session = await self._get_session()

                async with session.get(url) as resp:

                    html = await resp.text()

                    return {
                        "html": html,
                        "status": resp.status,
                        "content_type": resp.headers.get(
                            "Content-Type",
                            ""
                        )
                    }

            except Exception as e:

                print(
                    f"❌ Fetch error: "
                    f"{url} | {e}"
                )

                self.failed_count += 1

                return None

    # =====================================================
    # FETCH + SAVE
    # =====================================================

    async def fetch_and_save(
        self,
        url: str
    ):

        result = await self.fetch(url)

        if not result:
            return

        data = self.parser.parse(

            html=result["html"],

            url=url,

            status_code=result["status"],

            content_type=result["content_type"]
        )

        # =============================================
        # SAVE
        # =============================================

        try:

            await self.storage.save(data)

            self.saved_count += 1

        except Exception as e:

            print(
                f"❌ Storage error: {e}"
            )

    # =====================================================
    # CRAWL
    # =====================================================

    async def crawl(
        self,
        start_urls: List[str]
    ):

        tasks = [

            self.fetch_and_save(url)

            for url in start_urls
        ]

        await asyncio.gather(*tasks)

    # =====================================================
    # CLOSE
    # =====================================================

    async def close(self):

        if self.session:

            await self.session.close()

        await self.storage.close()


# =========================================================
# DEMO
# =========================================================

async def demo_json():

    print("\n📄 JSON STORAGE DEMO")

    storage = JSONStorage(
        "results.json"
    )

    crawler = AsyncCrawler(
        storage=storage
    )

    urls = [

        "https://example.com",

        "https://httpbin.org/html"
    ]

    await crawler.crawl(urls)

    await crawler.close()


async def demo_csv():

    print("\n📄 CSV STORAGE DEMO")

    storage = CSVStorage(
        "results.csv"
    )

    crawler = AsyncCrawler(
        storage=storage
    )

    urls = [

        "https://example.com",

        "https://httpbin.org/html"
    ]

    await crawler.crawl(urls)

    await crawler.close()


async def demo_sqlite():

    print("\n📄 SQLITE STORAGE DEMO")

    storage = SQLiteStorage(
        "crawler.db"
    )

    await storage.init_db()

    crawler = AsyncCrawler(
        storage=storage
    )

    urls = [

        "https://example.com",

        "https://httpbin.org/html",

        "https://httpbin.org/links/5/0"
    ]

    await crawler.crawl(urls)

    rows = await storage.read_all()

    print("\n📊 SQLITE DATA:")

    for row in rows:

        print(row)

    await crawler.close()


# =========================================================
# MAIN
# =========================================================

async def main():

    start = time.time()

    await demo_json()

    await demo_csv()

    await demo_sqlite()

    end = time.time()

    print(
        f"\n⏱️ Total time: "
        f"{end - start:.2f} sec"
    )


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    asyncio.run(main())