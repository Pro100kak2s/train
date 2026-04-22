from abc import ABC, abstractmethod
from enum import Enum
import uuid

#  ИСКЛЮЧЕНИЯ

class AccountError(Exception):
    """Базовая ошибка для всех операций со счетом"""
    pass


class AccountFrozenError(AccountError):
    """❄ Счет заморожен"""
    pass


class AccountClosedError(AccountError):
    """ Счет закрыт"""
    pass


class InvalidOperationError(AccountError):
    """ Некорректная операция"""
    pass


class InsufficientFundsError(AccountError):
    """ Недостаточно средств"""
    pass

#  ENUMЫ
class AccountStatus(Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"

class Currency(Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    KZT = "KZT"
    CNY = "CNY"


#  АБСТРАКТНЫЙ КЛАСС

class AbstractAccount(ABC):
    def __init__(self, owner: str, account_id: str = None):
        if not owner or not owner.strip():
            raise InvalidOperationError("Владелец не может быть пустым")

        # 🆔 короткий UUID
        self._id = account_id if account_id else str(uuid.uuid4())[:8]

        self._owner = owner
        self._balance = 0.0
        self._status = AccountStatus.ACTIVE

    @abstractmethod
    def deposit(self, amount: float):
        pass

    @abstractmethod
    def withdraw(self, amount: float):
        pass

    @abstractmethod
    def get_account_info(self):
        pass

    def get_balance(self):
        return self._balance

    def get_status(self):
        return self._status

    def get_id(self):
        return self._id


#  КОНКРЕТНЫЙ СЧЕТ

class BankAccount(AbstractAccount):

    def __init__(self, owner: str, currency: Currency, account_id: str = None):
        super().__init__(owner, account_id)

        if not isinstance(currency, Currency):
            raise InvalidOperationError("Неверная валюта")

        self._currency = currency

    #  Проверка статуса
    def _ensure_active(self):
        if self._status == AccountStatus.FROZEN:
            raise AccountFrozenError("Операции запрещены: счет заморожен")

        if self._status == AccountStatus.CLOSED:
            raise AccountClosedError("Операции запрещены: счет закрыт")

    #  Валидация суммы
    def _validate_amount(self, amount):
        if not isinstance(amount, (int, float)):
            raise InvalidOperationError("Сумма должна быть числом")

        if amount != amount or amount in (float("inf"), float("-inf")):
            raise InvalidOperationError("Некорректное число")

        if amount <= 0:
            raise InvalidOperationError("Сумма должна быть больше 0")

    # Пополнение
    def deposit(self, amount: float):
        self._ensure_active()
        self._validate_amount(amount)

        self._balance += amount

    #  Снятие
    def withdraw(self, amount: float):
        self._ensure_active()
        self._validate_amount(amount)

        if amount > self._balance:
            raise InsufficientFundsError("Недостаточно средств")

        self._balance -= amount

    #  Информация
    def get_account_info(self):
        return {
            "id": self._id,
            "owner": self._owner,
            "balance": round(self._balance, 2),
            "currency": self._currency.value,
            "status": self._status.value
        }

    #  Строковое представление
    def __str__(self):
        account_type = self.__class__.__name__
        last_digits = self._id[-4:]
        status = self._status.value
        balance = f"{round(self._balance, 2)} {self._currency.value}"

        return (
            f"{account_type} | "
            f"Клиент: {self._owner} | "
            f"Счет: ****{last_digits} | "
            f"Статус: {status} | "
            f"Баланс: {balance}"
        )

    #  Управление
    def freeze(self):
        if self._status == AccountStatus.CLOSED:
            raise AccountClosedError("Закрытый счет нельзя заморозить")

        self._status = AccountStatus.FROZEN

    def close(self):
        self._status = AccountStatus.CLOSED


#  ДЕМОНСТРАЦИЯ

def run_demo():
    print("\n=== ДЕМОНСТРАЦИЯ ===\n")

    #  активный счет
    print("1️⃣ Активный счет")
    active = BankAccount("Timofey", Currency.USD)
    print(active)

    #  операции
    print("\n2️⃣ Пополнение и снятие")
    active.deposit(1000)
    active.withdraw(200)
    print(active)

    #  замороженный счет
    print("\n3️⃣ Замороженный счет")
    frozen = BankAccount("Alex", Currency.EUR)
    frozen.freeze()
    print(frozen)

    #  операции на замороженном
    print("\n4️⃣ Попытки операций")
    try:
        frozen.deposit(100)
    except AccountFrozenError as e:
        print("Ожидаемая ошибка:", e)

    try:
        frozen.withdraw(50)
    except AccountFrozenError as e:
        print("Ожидаемая ошибка:", e)

    #  недостаточно средств
    print("\n5️⃣ Недостаточно средств")
    try:
        active.withdraw(10000)
    except InsufficientFundsError as e:
        print("Ожидаемая ошибка:", e)

    print("\n=== ГОТОВО ===\n")


# запуск
if __name__ == "__main__":
    run_demo()