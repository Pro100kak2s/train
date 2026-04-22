from abc import ABC, abstractmethod
from enum import Enum
import uuid

# =========================================================
#  3. ИСКЛЮЧЕНИЯ
# =========================================================

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


# =========================================================
#  ENUMЫ
# =========================================================

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


# =========================================================
#  1. АБСТРАКТНЫЙ КЛАСС
# =========================================================

class AbstractAccount(ABC):
    def __init__(self, owner: str, account_id: str = None):
        #  Валидация владельца
        if not owner or not owner.strip():
            raise InvalidOperationError("Владелец не может быть пустым")

        #  Генерация короткого UUID (8 символов)
        self._id = account_id if account_id else str(uuid.uuid4())[:8]

        #  Владелец
        self._owner = owner

        #  Баланс (инкапсуляция)
        self._balance = 0.0

        #  Статус
        self._status = AccountStatus.ACTIVE

    #  Абстрактные методы
    @abstractmethod
    def deposit(self, amount: float):
        pass

    @abstractmethod
    def withdraw(self, amount: float):
        pass

    @abstractmethod
    def get_account_info(self):
        pass

    #  Общие геттеры
    def get_balance(self):
        return self._balance

    def get_status(self):
        return self._status

    def get_id(self):
        return self._id


# =========================================================
#  2. КОНКРЕТНЫЙ СЧЕТ
# =========================================================

class BankAccount(AbstractAccount):

    def __init__(self, owner: str, currency: Currency, account_id: str = None):
        super().__init__(owner, account_id)

        #  Валидация валюты
        if not isinstance(currency, Currency):
            raise InvalidOperationError("Неверная валюта")

        self._currency = currency

    #  Проверка статуса
    def _ensure_active(self):
        if self._status == AccountStatus.FROZEN:
            raise AccountFrozenError("Операции запрещены: счет заморожен")

        if self._status == AccountStatus.CLOSED:
            raise AccountClosedError("Операции запрещены: счет закрыт")

    #  Пополнение
    def deposit(self, amount: float):
        self._ensure_active()

        if not isinstance(amount, (int, float)):
            raise InvalidOperationError("Сумма должна быть числом")

        if amount <= 0:
            raise InvalidOperationError("Сумма должна быть больше 0")

        self._balance += amount

    #  Снятие
    def withdraw(self, amount: float):
        self._ensure_active()

        if not isinstance(amount, (int, float)):
            raise InvalidOperationError("Сумма должна быть числом")

        if amount <= 0:
            raise InvalidOperationError("Сумма должна быть больше 0")

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

    #  Управление счетом
    def freeze(self):
        if self._status == AccountStatus.CLOSED:
            raise AccountClosedError("Закрытый счет нельзя заморозить")

        self._status = AccountStatus.FROZEN

    def close(self):
        self._status = AccountStatus.CLOSED



if __name__ == "__main__":
    acc = BankAccount("Timofey", Currency.USD)

    try:
        acc.deposit(1000)
        acc.withdraw(200)

        print(acc.get_account_info())

        acc.freeze()
        acc.withdraw(100)  # вызовет AccountFrozenError

    except AccountError as e:
        print(f"Ошибка: {e}")