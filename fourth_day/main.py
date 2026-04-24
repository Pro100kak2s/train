from enum import Enum
import uuid
import time

from first_day.main import Currency, BankAccount, InsufficientFundsError, AccountFrozenError, AccountStatus
from second_day.main import PremiumAccount


# =========================
# ENUMЫ
# =========================

class TransactionStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransactionType(Enum):
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"


# =========================
# КОНВЕРТАЦИЯ
# =========================

class CurrencyConverter:
    RATES = {
        ("USD", "EUR"): 0.9,
        ("EUR", "USD"): 1.1,
        ("USD", "USD"): 1,
    }

    @staticmethod
    def convert(amount, from_currency, to_currency):
        rate = CurrencyConverter.RATES.get(
            (from_currency.value, to_currency.value),
            1
        )
        return amount * rate


# =========================
# TRANSACTION
# =========================

class Transaction:
    def __init__(self, t_type, amount, currency, sender=None, receiver=None, fee=0):
        self.id = str(uuid.uuid4())[:8]

        self.type = t_type
        self.amount = amount
        self.currency = currency
        self.fee = fee

        self.sender = sender
        self.receiver = receiver

        self.status = TransactionStatus.PENDING
        self.error = None

        self.attempts = 0
        self.max_attempts = 3

        self.created_at = time.time()
        self.processed_at = None

    def __str__(self):
        return f"{self.type.value} | {round(self.amount, 2)} {self.currency.value} | {self.status.value}"


# =========================
# QUEUE
# =========================

class TransactionQueue:
    def __init__(self):
        self.queue = []

    def add(self, transaction, priority=0, delay=0):
        execute_at = time.time() + delay

        self.queue.append({
            "transaction": transaction,
            "priority": priority,
            "execute_at": execute_at
        })

    def cancel(self, transaction_id):
        for item in self.queue:
            if item["transaction"].id == transaction_id:
                item["transaction"].status = TransactionStatus.CANCELLED
                self.queue.remove(item)  # FIX
                return True
        return False

    def get_next(self):
        now = time.time()

        self.queue.sort(key=lambda x: x["priority"], reverse=True)

        for item in self.queue:
            tx = item["transaction"]

            if tx.status == TransactionStatus.CANCELLED:
                continue  # FIX

            if item["execute_at"] <= now:
                return item

        return None

    def remove(self, item):
        self.queue.remove(item)


# =========================
# PROCESSOR
# =========================

class TransactionProcessor:
    def __init__(self):
        self.log = []

    def process(self, transaction: Transaction):
        try:
            transaction.attempts += 1

            # статус счетов
            if transaction.sender and transaction.sender.get_status() != AccountStatus.ACTIVE:
                raise AccountFrozenError("Счет отправителя недоступен")

            if transaction.receiver and transaction.receiver.get_status() != AccountStatus.ACTIVE:
                raise AccountFrozenError("Счет получателя недоступен")

            total = transaction.amount + transaction.fee

            # проверка средств
            if transaction.sender:
                if not isinstance(transaction.sender, PremiumAccount):
                    if transaction.sender.get_balance() < total:
                        raise InsufficientFundsError("Недостаточно средств")

            # конвертация
            if transaction.sender and transaction.receiver:
                if transaction.sender._currency != transaction.receiver._currency:
                    transaction.amount = CurrencyConverter.convert(
                        transaction.amount,
                        transaction.sender._currency,
                        transaction.receiver._currency
                    )

            # выполнение
            if transaction.type == TransactionType.TRANSFER:
                transaction.sender.withdraw(total)
                transaction.receiver.deposit(transaction.amount)

            elif transaction.type == TransactionType.DEPOSIT:
                transaction.receiver.deposit(transaction.amount)

            elif transaction.type == TransactionType.WITHDRAW:
                transaction.sender.withdraw(transaction.amount)

            transaction.status = TransactionStatus.SUCCESS

        except Exception as e:
            if transaction.attempts < transaction.max_attempts:
                transaction.status = TransactionStatus.PENDING  # retry
            else:
                transaction.status = TransactionStatus.FAILED
                transaction.error = str(e)

        finally:
            transaction.processed_at = time.time()
            self.log.append(transaction)


# =========================
# DEMO
# =========================

def run_day4_demo():
    print("\n=== DAY 4 DEMO ===\n")

    acc1 = BankAccount("Timofey", Currency.USD)
    acc2 = PremiumAccount("Alex", Currency.USD, 500, 5)
    acc3 = BankAccount("John", Currency.USD)

    acc1.deposit(1000)
    acc2.deposit(100)
    acc3.deposit(50)

    acc3.freeze()

    queue = TransactionQueue()
    processor = TransactionProcessor()

    # норм
    for _ in range(3):
        queue.add(Transaction(
            TransactionType.TRANSFER, 100, Currency.USD,
            sender=acc1, receiver=acc2, fee=2
        ))

    # минус ошибка
    queue.add(Transaction(
        TransactionType.TRANSFER, 2000, Currency.USD,
        sender=acc1, receiver=acc2, fee=2
    ))

    # premium минус
    queue.add(Transaction(
        TransactionType.TRANSFER, 400, Currency.USD,
        sender=acc2, receiver=acc1, fee=5
    ))

    # frozen
    queue.add(Transaction(
        TransactionType.TRANSFER, 10, Currency.USD,
        sender=acc3, receiver=acc1, fee=1
    ))

    # обработка
    while True:
        item = queue.get_next()
        if not item:
            break

        tx = item["transaction"]

        processor.process(tx)

        if tx.status == TransactionStatus.PENDING:
            continue  # retry

        queue.remove(item)
        print(tx)

    print("\n=== LOG ===")
    for t in processor.log:
        print(f"{t.id} | {t.status.value} | {t.error}")

    print("\n=== BALANCES ===")
    print("Timofey:", acc1.get_balance())
    print("Alex:", acc2.get_balance())
    print("John:", acc3.get_balance())


if __name__ == "__main__":
    run_day4_demo()