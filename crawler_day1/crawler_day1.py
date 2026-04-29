import asyncio
import aiohttp
import time
from typing import List, Dict, Optional


class AsyncCrawler:
    """
    Асинхронный HTTP-клиент для параллельной загрузки страниц
    """

    def __init__(self, max_concurrent: int = 10, timeout: int = 10):
        """
        :param max_concurrent: Максимальное количество одновременных запросов
        :param timeout: Таймаут запроса (в секундах)
        """

        # Ограничение конкурентности (Semaphore)
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # Настройка таймаутов aiohttp
        self.timeout = aiohttp.ClientTimeout(
            total=timeout,          # общий таймаут
            connect=5,              # таймаут на соединение
            sock_read=5             # таймаут на чтение
        )

        # Сессия (будет создана позже)
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Ленивая инициализация ClientSession (создается один раз)
        """
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def fetch_url(self, url: str) -> Optional[str]:
        """
        Загружает одну страницу

        :param url: URL страницы
        :return: HTML страницы или None при ошибке
        """

        # Ограничиваем количество параллельных запросов
        async with self.semaphore:
            print(f"▶️ Начало загрузки: {url}")

            try:
                session = await self._get_session()

                async with session.get(url) as response:
                    # Проверка HTTP статуса (400+ -> ошибка)
                    response.raise_for_status()

                    text = await response.text()

                    print(f"✅ Успешно: {url} (status={response.status})")
                    return text

            except aiohttp.ClientResponseError as e:
                print(f"🚫 HTTP ошибка: {url} | status={e.status}")

            except aiohttp.ClientError as e:
                print(f"❌ Сетевая ошибка: {url} | {e}")

            except asyncio.TimeoutError:
                print(f"⏰ Таймаут: {url}")

            except Exception as e:
                print(f"⚠️ Неизвестная ошибка: {url} | {e}")

            return None

    async def fetch_urls(self, urls: List[str]) -> Dict[str, Optional[str]]:
        """
        Параллельно загружает список URL

        :param urls: список URL
        :return: словарь {url: content}
        """

        # Создаем задачи
        tasks = [self.fetch_url(url) for url in urls]

        # Параллельное выполнение
        results = await asyncio.gather(*tasks)

        # Собираем результат в словарь
        return dict(zip(urls, results))

    async def close(self):
        """
        Закрывает сессию
        """
        if self.session:
            await self.session.close()
            print("🔒 Сессия закрыта")


# ==========================
# Демонстрация
# ==========================

async def run_parallel(crawler: AsyncCrawler, urls: List[str]):
    print("\n🚀 ПАРАЛЛЕЛЬНАЯ ЗАГРУЗКА")
    start = time.time()

    results = await crawler.fetch_urls(urls)

    end = time.time()
    print(f"\n⏱️ Время (параллельно): {end - start:.2f} сек")

    for url, content in results.items():
        status = "OK" if content else "ERROR"
        print(f"{url} -> {status}")


async def run_sequential(crawler: AsyncCrawler, urls: List[str]):
    print("\n🐢 ПОСЛЕДОВАТЕЛЬНАЯ ЗАГРУЗКА")
    start = time.time()

    results = {}
    for url in urls:
        results[url] = await crawler.fetch_url(url)

    end = time.time()
    print(f"\n⏱️ Время (последовательно): {end - start:.2f} сек")

    for url, content in results.items():
        status = "OK" if content else "ERROR"
        print(f"{url} -> {status}")


async def main():
    crawler = AsyncCrawler(max_concurrent=5)

    urls = [
        "https://example.com",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/2",
        "https://httpbin.org/status/404",  # ошибка
        "https://invalid-url-test.xyz",    # ошибка сети
    ]

    await run_sequential(crawler, urls)
    await run_parallel(crawler, urls)

    await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())