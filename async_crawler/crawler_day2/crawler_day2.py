import asyncio
import aiohttp
import time
import json

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


# ==========================================
# HTML PARSER
# ==========================================

class HTMLParser:
    """
    Класс для парсинга HTML и извлечения данных
    """

    async def parse_html(self, html: str, url: str) -> dict:

        try:
            soup = BeautifulSoup(html, "lxml")

            title = (
                soup.title.string.strip()
                if soup.title and soup.title.string
                else ""
            )

            text = self.extract_text(soup)

            links = self.extract_links(soup, url)

            metadata = self.extract_metadata(soup)

            images = self.extract_images(soup, url)

            headings = self.extract_headings(soup)

            tables = self.extract_tables(soup)

            lists_data = self.extract_lists(soup)

            return {
                "url": url,

                "title": title,

                "text": text,
                "text_length": len(text),

                "links": links,
                "links_count": len(links),

                "metadata": metadata,

                "images": images,
                "images_count": len(images),

                "headings": headings,

                "tables": tables,
                "tables_count": len(tables),

                "unordered_lists": lists_data["unordered_lists"],
                "ordered_lists": lists_data["ordered_lists"],
            }

        except Exception as e:

            print(f"⚠️ Ошибка парсинга HTML: {url} | {e}")

            return {
                "url": url,
                "error": str(e)
            }

    # ==========================================
    # TEXT
    # ==========================================

    def extract_text(
        self,
        soup: BeautifulSoup,
        selector: str = None
    ) -> str:

        if selector:

            elements = soup.select(selector)

            return " ".join(
                el.get_text(strip=True)
                for el in elements
            )

        return soup.get_text(
            separator=" ",
            strip=True
        )

    # ==========================================
    # LINKS
    # ==========================================

    def extract_links(
        self,
        soup: BeautifulSoup,
        base_url: str
    ) -> List[str]:

        links = []

        for a_tag in soup.find_all("a", href=True):

            href = a_tag.get("href")

            absolute_url = urljoin(base_url, href)

            if self._is_valid_url(absolute_url):
                links.append(absolute_url)

        return list(set(links))

    # ==========================================
    # METADATA
    # ==========================================

    def extract_metadata(
        self,
        soup: BeautifulSoup
    ) -> Dict[str, str]:

        metadata = {}

        for meta in soup.find_all("meta"):

            name = meta.get("name") or meta.get("property")

            content = meta.get("content")

            if name and content:
                metadata[name.lower()] = content

        return metadata

    # ==========================================
    # IMAGES
    # ==========================================

    def extract_images(
        self,
        soup: BeautifulSoup,
        base_url: str
    ) -> List[Dict]:

        images = []

        for img in soup.find_all("img"):

            src = img.get("src")

            alt = img.get("alt", "")

            if src:

                images.append({
                    "src": urljoin(base_url, src),
                    "alt": alt
                })

        return images

    # ==========================================
    # HEADINGS
    # ==========================================

    def extract_headings(
        self,
        soup: BeautifulSoup
    ) -> Dict[str, List[str]]:

        headings = {}

        for level in ["h1", "h2", "h3"]:

            headings[level] = [

                tag.get_text(strip=True)

                for tag in soup.find_all(level)
            ]

        return headings

    # ==========================================
    # TABLES
    # ==========================================

    def extract_tables(
        self,
        soup: BeautifulSoup
    ) -> List[List[List[str]]]:

        tables = []

        for table in soup.find_all("table"):

            table_data = []

            for row in table.find_all("tr"):

                row_data = []

                cells = row.find_all(["td", "th"])

                for cell in cells:

                    row_data.append(
                        cell.get_text(strip=True)
                    )

                if row_data:
                    table_data.append(row_data)

            if table_data:
                tables.append(table_data)

        return tables

    # ==========================================
    # LISTS
    # ==========================================

    def extract_lists(
        self,
        soup: BeautifulSoup
    ) -> Dict[str, List[List[str]]]:

        unordered = []

        ordered = []

        # UL

        for ul in soup.find_all("ul"):

            items = [

                li.get_text(strip=True)

                for li in ul.find_all("li")
            ]

            if items:
                unordered.append(items)

        # OL

        for ol in soup.find_all("ol"):

            items = [

                li.get_text(strip=True)

                for li in ol.find_all("li")
            ]

            if items:
                ordered.append(items)

        return {
            "unordered_lists": unordered,
            "ordered_lists": ordered
        }

    # ==========================================
    # URL VALIDATION
    # ==========================================

    def _is_valid_url(self, url: str) -> bool:

        parsed = urlparse(url)

        return bool(
            parsed.scheme and parsed.netloc
        )


# ==========================================
# ASYNC CRAWLER
# ==========================================

class AsyncCrawler:
    def __init__(self, max_concurrent: int = 10):

        self.semaphore = asyncio.Semaphore(
            max_concurrent
        )

        self.session: Optional[
            aiohttp.ClientSession
        ] = None

        self.parser = HTMLParser()

    async def _get_session(self):

        if not self.session:

            timeout = aiohttp.ClientTimeout(
                total=20
            )

            self.session = aiohttp.ClientSession(
                timeout=timeout
            )

        return self.session

    async def fetch(
        self,
        url: str
    ) -> Optional[str]:

        async with self.semaphore:

            print(f"▶️ Fetch: {url}")

            try:

                session = await self._get_session()

                async with session.get(url) as response:

                    response.raise_for_status()

                    return await response.text()

            except Exception as e:

                print(f"❌ Ошибка: {url} | {e}")

                return None

    async def fetch_and_parse(
        self,
        url: str
    ) -> dict:

        html = await self.fetch(url)

        if not html:

            return {
                "url": url,
                "error": "fetch failed"
            }

        return await self.parser.parse_html(
            html,
            url
        )

    async def fetch_many(
        self,
        urls: List[str]
    ) -> List[dict]:

        tasks = [

            self.fetch_and_parse(url)

            for url in urls
        ]

        return await asyncio.gather(*tasks)

    async def close(self):

        if self.session:
            await self.session.close()


# ==========================================
# DEMO
# ==========================================

async def main():

    crawler = AsyncCrawler(max_concurrent=5)

    urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://httpbin.org/links/5/0"
    ]

    start = time.time()

    results = await crawler.fetch_many(urls)

    end = time.time()

    print(f"\n⏱️ Время: {end - start:.2f} сек")

    with open(
        "results.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False
        )

    for r in results:

        print({
            "url": r.get("url"),
            "title": r.get("title"),
            "links_count": r.get("links_count"),
            "tables_count": r.get("tables_count"),
            "images_count": r.get("images_count"),
        })

    await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())