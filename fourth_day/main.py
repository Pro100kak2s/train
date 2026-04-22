from enum import Enum
import uuid
import time

from first_day.main import Currency, BankAccount, InsufficientFundsError, AccountFrozenError, AccountStatus
from second_day.main import PremiumAccount


# ENUMЫ ДЛЯ ТРАНЗАКЦИЙ

class TransactionStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransactionType(Enum):
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"

# TRANSACTION

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

        self.created_at = time.time()
        self.processed_at = None

    def __str__(self):
        return f"{self.type.value} | {self.amount} {self.currency.value} | {self.status.value}"


# TRANSACTION QUEUE

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
                return True
        return False

    def get_next(self):
        now = time.time()

        # сортировка по приоритету
        self.queue.sort(key=lambda x: x["priority"], reverse=True)

        for item in self.queue:
            if item["execute_at"] <= now:
                return item

        return None

    def remove(self, item):
        self.queue.remove(item)


# TRANSACTION PROCESSOR

class TransactionProcessor:
    def __init__(self):
        self.log = []

    def process(self, transaction: Transaction):
        try:
            #  проверка статуса счета
            if transaction.sender and transaction.sender.get_status() != AccountStatus.ACTIVE:
                raise AccountFrozenError("Счет отправителя недоступен")

            if transaction.receiver and transaction.receiver.get_status() != AccountStatus.ACTIVE:
                raise AccountFrozenError("Счет получателя недоступен")

            #  комиссия
            total_amount = transaction.amount + transaction.fee

            #  запрет минуса (кроме Premium)
            if transaction.sender:
                if isinstance(transaction.sender, PremiumAccount):
                    pass
                else:
                    if transaction.sender.get_balance() < total_amount:
                        raise InsufficientFundsError("Недостаточно средств")

            #  (упрощенная конвертация — без реального курса)
            if transaction.sender and transaction.receiver:
                if transaction.sender._currency != transaction.receiver._currency:
                    transaction.amount *= 1  # заглушка

            # выполнение
            if transaction.type == TransactionType.TRANSFER:
                transaction.sender.withdraw(transaction.amount + transaction.fee)
                transaction.receiver.deposit(transaction.amount)

            elif transaction.type == TransactionType.DEPOSIT:
                transaction.receiver.deposit(transaction.amount)

            elif transaction.type == TransactionType.WITHDRAW:
                transaction.sender.withdraw(transaction.amount)

            transaction.status = TransactionStatus.SUCCESS

        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.error = str(e)

        finally:
            transaction.processed_at = time.time()
            self.log.append(transaction)

def run_day4_demo():
    print("\n=== DAY 4 DEMO ===\n")

    # счета
    acc1 = BankAccount("Timofey", Currency.USD)
    acc2 = PremiumAccount("Alex", Currency.USD, 500, 5)
    acc3 = BankAccount("John", Currency.USD)

    acc1.deposit(1000)
    acc2.deposit(100)
    acc3.deposit(50)

    # ️ замораживаем счет
    acc3.freeze()

    queue = TransactionQueue()
    processor = TransactionProcessor()

    # ===============================
    # 1. НОРМАЛЬНЫЕ ТРАНЗАКЦИИ
    # ===============================
    for i in range(3):
        t = Transaction(
            TransactionType.TRANSFER,
            amount=100,
            currency=Currency.USD,
            sender=acc1,
            receiver=acc2,
            fee=2
        )
        queue.add(t)

    # ===============================
    # 2. ОБЫЧНЫЙ СЧЕТ В МИНУС (ошибка)
    # ===============================
    t_fail_minus = Transaction(
        TransactionType.TRANSFER,
        amount=2000,  # больше баланса
        currency=Currency.USD,
        sender=acc1,
        receiver=acc2,
        fee=2
    )
    queue.add(t_fail_minus)

    # ===============================
    # 3. PREMIUM УХОДИТ В МИНУС (норм)
    # ===============================
    t_premium_minus = Transaction(
        TransactionType.TRANSFER,
        amount=400,  # уйдет в минус, но в лимите
        currency=Currency.USD,
        sender=acc2,
        receiver=acc1,
        fee=5
    )
    queue.add(t_premium_minus)

    # ===============================
    # 4.️ ЗАМОРОЖЕННЫЙ СЧЕТ (ошибка)
    # ===============================
    t_frozen = Transaction(
        TransactionType.TRANSFER,
        amount=10,
        currency=Currency.USD,
        sender=acc3,  # заморожен
        receiver=acc1,
        fee=1
    )
    queue.add(t_frozen)

    # ===============================
    # ОБРАБОТКА
    # ===============================
    while True:
        item = queue.get_next()

        if not item:
            break

        transaction = item["transaction"]

        processor.process(transaction)
        queue.remove(item)

        print(transaction)

    # ===============================
    # ЛОГ
    # ===============================
    print("\n=== LOG ===")
    for t in processor.log:
        print(
            f"ID: {t.id} | STATUS: {t.status.value} | ERROR: {t.error}"
        )

    # ===============================
    # БАЛАНСЫ
    # ===============================
    print("\n=== FINAL BALANCES ===")
    print("Timofey:", acc1.get_balance())
    print("Alex (Premium):", acc2.get_balance())
    print("John (Frozen):", acc3.get_balance())


if __name__ == "__main__":
    run_day4_demo()