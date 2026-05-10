import asyncio
import aiohttp
import time
import json

from typing import Dict, List, Optional, Type
from urllib.parse import urlparse

from bs4 import BeautifulSoup


# =========================================================
# ERRORS
# =========================================================

class CrawlerError(Exception):
    """
    Базовая ошибка crawler
    """
    pass


class TransientError(CrawlerError):
    """
    Временная ошибка

    Можно повторять:
    - 429
    - 503
    - timeout
    """
    pass


class PermanentError(CrawlerError):
    """
    Постоянная ошибка

    Повторять нельзя:
    - 404
    - 403
    - 401
    """
    pass


class NetworkError(TransientError):
    """
    Сетевые ошибки
    """
    pass


class ParseError(CrawlerError):
    """
    Ошибки парсинга
    """
    pass


# =========================================================
# CIRCUIT BREAKER
# =========================================================

class CircuitBreaker:
    """
    Блокировка домена при большом
    количестве ошибок
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 15
    ):

        self.failure_threshold = failure_threshold

        self.recovery_timeout = recovery_timeout

        self.failures: Dict[str, int] = {}

        self.blocked_until: Dict[str, float] = {}

    def is_blocked(self, domain: str) -> bool:

        if domain not in self.blocked_until:
            return False

        current_time = time.time()

        unblock_time = self.blocked_until[domain]

        # ещё заблокирован

        if current_time < unblock_time:
            return True

        # разблокируем

        del self.blocked_until[domain]

        self.failures[domain] = 0

        return False

    def record_failure(self, domain: str):

        self.failures[domain] = (
            self.failures.get(domain, 0) + 1
        )

        if (
            self.failures[domain]
            >= self.failure_threshold
        ):

            self.blocked_until[domain] = (
                time.time() + self.recovery_timeout
            )

            print(
                f"🚫 Circuit OPEN for {domain}"
            )

    def record_success(self, domain: str):

        self.failures[domain] = 0


# =========================================================
# RETRY STRATEGY
# =========================================================

class RetryStrategy:
    """
    Управление retry логикой
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        retry_on: list = None
    ):

        self.max_retries = max_retries

        self.backoff_factor = backoff_factor

        self.retry_on = retry_on or [
            TransientError,
            NetworkError
        ]

        # =========================================
        # STATS
        # =========================================

        self.stats = {
            "errors_by_type": {},
            "successful_retries": 0,
            "retry_times": [],
            "permanent_errors": []
        }

    # =====================================================
    # BACKOFF
    # =====================================================

    def get_backoff_time(
        self,
        error: Exception,
        attempt: int
    ) -> float:

        base = self.backoff_factor ** attempt

        # 429 → сильнее замедляемся

        if isinstance(error, TransientError):

            if "429" in str(error):
                return base * 3

            if "503" in str(error):
                return base * 2

        return base

    # =====================================================
    # EXECUTE WITH RETRY
    # =====================================================

    async def execute_with_retry(
        self,
        coro,
        *args,
        **kwargs
    ):

        attempt = 0

        while attempt <= self.max_retries:

            retry_start = time.time()

            try:

                result = await coro(
                    *args,
                    **kwargs
                )

                # success after retry

                if attempt > 0:

                    self.stats[
                        "successful_retries"
                    ] += 1

                    retry_time = (
                        time.time() - retry_start
                    )

                    self.stats[
                        "retry_times"
                    ].append(retry_time)

                return result

            except Exception as e:

                error_name = type(e).__name__

                # =================================
                # STATS
                # =================================

                self.stats["errors_by_type"][
                    error_name
                ] = (
                    self.stats["errors_by_type"].get(
                        error_name,
                        0
                    ) + 1
                )

                # =================================
                # SHOULD RETRY
                # =================================

                should_retry = any(

                    isinstance(e, retry_type)

                    for retry_type in self.retry_on
                )

                # =================================
                # LOGGING
                # =================================

                print(
                    f"\n❌ ERROR:"
                    f"\nType: {error_name}"
                    f"\nAttempt: {attempt + 1}"
                    f"\nError: {e}"
                )

                # =================================
                # NO RETRY
                # =================================

                if not should_retry:

                    print(
                        "🚫 Permanent error. "
                        "No retry."
                    )

                    self.stats[
                        "permanent_errors"
                    ].append(str(e))

                    raise

                # =================================
                # MAX RETRIES
                # =================================

                if attempt >= self.max_retries:

                    print(
                        "❌ Max retries exceeded"
                    )

                    raise

                # =================================
                # BACKOFF
                # =================================

                backoff = self.get_backoff_time(
                    e,
                    attempt
                )

                print(
                    f"⏳ Retry in "
                    f"{backoff:.2f} sec"
                )

                await asyncio.sleep(backoff)

                attempt += 1

    # =====================================================
    # STATS
    # =====================================================

    def get_stats(self):

        avg_retry_time = 0

        if self.stats["retry_times"]:

            avg_retry_time = (
                sum(self.stats["retry_times"])
                /
                len(self.stats["retry_times"])
            )

        return {
            **self.stats,
            "avg_retry_time": avg_retry_time
        }


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
        url: str
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

            return {
                "url": url,
                "title": title
            }

        except Exception as e:

            raise ParseError(
                f"Parse error: {url} | {e}"
            )


# =========================================================
# ASYNC CRAWLER
# =========================================================

class AsyncCrawler:
    """
    Production-like crawler
    """

    def __init__(
        self,
        max_concurrent: int = 5
    ):

        self.semaphore = asyncio.Semaphore(
            max_concurrent
        )

        self.parser = HTMLParser()

        self.session = None

        self.retry_strategy = RetryStrategy(
            max_retries=3,
            backoff_factor=2.0,
            retry_on=[
                TransientError,
                NetworkError
            ]
        )

        self.circuit_breaker = CircuitBreaker()

        self.errors: List[Dict] = []

    # =====================================================
    # SESSION
    # =====================================================

    async def _get_session(
        self,
        timeout_multiplier: int = 1
    ):

        timeout = aiohttp.ClientTimeout(

            total=10 * timeout_multiplier,

            connect=5 * timeout_multiplier,

            sock_read=5 * timeout_multiplier
        )

        if not self.session:

            self.session = aiohttp.ClientSession(
                timeout=timeout
            )

        return self.session

    # =====================================================
    # FETCH URL
    # =====================================================

    async def fetch_url(
        self,
        url: str,
        timeout_multiplier: int = 1
    ) -> str:

        async with self.semaphore:

            domain = urlparse(url).netloc

            # =====================================
            # CIRCUIT BREAKER
            # =====================================

            if self.circuit_breaker.is_blocked(
                domain
            ):

                raise TransientError(
                    f"Domain blocked: {domain}"
                )

            try:

                session = await self._get_session(
                    timeout_multiplier
                )

                async with session.get(url) as response:

                    status = response.status

                    print(
                        f"🌐 {url} -> {status}"
                    )

                    # =============================
                    # SUCCESS
                    # =============================

                    if status == 200:

                        self.circuit_breaker.record_success(
                            domain
                        )

                        return await response.text()

                    # =============================
                    # RETRYABLE
                    # =============================

                    if status == 429:

                        raise TransientError(
                            "429 Too Many Requests"
                        )

                    if status == 503:

                        raise TransientError(
                            "503 Service Unavailable"
                        )

                    if status == 500:

                        raise TransientError(
                            "500 Internal Server Error"
                        )

                    # =============================
                    # PERMANENT
                    # =============================

                    if status in [401, 403, 404]:

                        raise PermanentError(
                            f"{status} Permanent error"
                        )

                    raise CrawlerError(
                        f"Unhandled status: {status}"
                    )

            except asyncio.TimeoutError:

                self.circuit_breaker.record_failure(
                    domain
                )

                raise TransientError(
                    "Timeout error"
                )

            except aiohttp.ClientConnectionError:

                self.circuit_breaker.record_failure(
                    domain
                )

                raise NetworkError(
                    "Connection error"
                )

            except Exception:

                self.circuit_breaker.record_failure(
                    domain
                )

                raise

    # =====================================================
    # FETCH + PARSE
    # =====================================================

    async def fetch_and_parse(
        self,
        url: str
    ) -> dict:

        try:

            html = await self.retry_strategy.execute_with_retry(
                self.fetch_url,
                url
            )

            return self.parser.parse(
                html,
                url
            )

        except Exception as e:

            self.errors.append({
                "url": url,
                "error": str(e),
                "type": type(e).__name__
            })

            return {
                "url": url,
                "error": str(e)
            }

    # =====================================================
    # FETCH MANY
    # =====================================================

    async def fetch_many(
        self,
        urls: List[str]
    ):

        tasks = [

            self.fetch_and_parse(url)

            for url in urls
        ]

        return await asyncio.gather(*tasks)

    # =====================================================
    # SAVE REPORT
    # =====================================================

    def save_error_report(
        self,
        filename: str = "error_report.json"
    ):

        report = {
            "errors": self.errors,
            "stats": self.retry_strategy.get_stats()
        }

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
    # CLOSE
    # =====================================================

    async def close(self):

        if self.session:

            await self.session.close()


# =========================================================
# DEMO
# =========================================================

async def main():

    crawler = AsyncCrawler(
        max_concurrent=5
    )

    urls = [

        # SUCCESS
        "https://example.com",

        # 503
        "https://httpbin.org/status/503",

        # 404
        "https://httpbin.org/status/404",

        # 429
        "https://httpbin.org/status/429",

        # TIMEOUT
        "https://httpbin.org/delay/15",
    ]

    start = time.time()

    try:

        results = await crawler.fetch_many(
            urls
        )

        end = time.time()

        print(
            f"\n⏱️ Total time: "
            f"{end - start:.2f} sec"
        )

        # =====================================
        # RESULTS
        # =====================================

        print("\n📄 RESULTS:")

        for result in results:

            print(result)

        # =====================================
        # STATS
        # =====================================

        print("\n📊 RETRY STATS:")

        stats = crawler.retry_strategy.get_stats()

        for key, value in stats.items():

            print(f"{key}: {value}")

        # =====================================
        # SAVE REPORT
        # =====================================

        crawler.save_error_report()

        print(
            "\n💾 Error report saved "
            "to error_report.json"
        )

    finally:

        await crawler.close()


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    asyncio.run(main())