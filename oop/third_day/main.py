import datetime

from oop.first_day.main import (
    AccountFrozenError,
    InvalidOperationError,
    AccountStatus,
    Currency,
    BankAccount
)
from oop.second_day.main import PremiumAccount


# =========================================================
# CLIENT
# =========================================================

class Client:
    def __init__(self, full_name, client_id, age, contacts):
        if age < 18:
            raise InvalidOperationError("Клиент должен быть старше 18")

        self.full_name = full_name
        self.client_id = client_id
        self.age = age
        self.contacts = contacts

        self.status = "active"
        self.account_ids = []

        self.failed_attempts = 0
        self.is_blocked = False
        self.suspicious_activity = False

    def add_account(self, account):
        self.account_ids.append(account.get_id())

    def __str__(self):
        return f"{self.full_name} | ID: {self.client_id} | Accounts: {len(self.account_ids)}"


# =========================================================
# BANK
# =========================================================

class Bank:
    def __init__(self):
        self.clients = {}
        self.accounts = {}

    # -----------------------------
    # Время
    # -----------------------------
    def _check_time(self):
        hour = datetime.datetime.now().hour
        if 0 <= hour < 5:
            raise InvalidOperationError("Операции запрещены ночью")

    # -----------------------------
    # Клиенты
    # -----------------------------
    def add_client(self, client: Client):
        self.clients[client.client_id] = client

    def authenticate_client(self, client_id, password_correct: bool):
        client = self.clients.get(client_id)

        if not client:
            raise InvalidOperationError("Клиент не найден")

        if client.is_blocked:
            raise InvalidOperationError("Клиент заблокирован")

        if not password_correct:
            client.failed_attempts += 1
            print(f"Неверный пароль ({client.failed_attempts}/3)")

            if client.failed_attempts >= 3:
                client.is_blocked = True
                client.suspicious_activity = True
                print("Клиент заблокирован")

            return False

        client.failed_attempts = 0
        print("Успешный вход")
        return True

    # -----------------------------
    # Счета
    # -----------------------------
    def open_account(self, client_id, account):
        self._check_time()

        client = self.clients.get(client_id)
        if not client:
            raise InvalidOperationError("Клиент не найден")

        client.add_account(account)
        self.accounts[account.get_id()] = account

    def close_account(self, account_id):
        account = self.accounts.get(account_id)
        if not account:
            raise InvalidOperationError("Счет не найден")

        account.close()

    def freeze_account(self, account_id):
        account = self.accounts.get(account_id)
        if not account:
            raise InvalidOperationError("Счет не найден")

        account.freeze()

    def unfreeze_account(self, account_id):
        account = self.accounts.get(account_id)
        if not account:
            raise InvalidOperationError("Счет не найден")

        if account.get_status() == AccountStatus.FROZEN:
            account._status = AccountStatus.ACTIVE

    def search_accounts(self, client_id):
        client = self.clients.get(client_id)
        if not client:
            raise InvalidOperationError("Клиент не найден")

        return [self.accounts[a] for a in client.account_ids]

    # -----------------------------
    # Финансы
    # -----------------------------
    def get_total_balance(self, client_id):
        client = self.clients.get(client_id)
        if not client:
            raise InvalidOperationError("Клиент не найден")

        return sum(self.accounts[a].get_balance() for a in client.account_ids)

    def get_clients_ranking(self):
        ranking = []

        for client in self.clients.values():
            total = sum(
                self.accounts[a].get_balance()
                for a in client.account_ids
            )
            ranking.append((client.full_name, total))

        return sorted(ranking, key=lambda x: x[1], reverse=True)


# =========================================================
# DEMO
# =========================================================

def run_day3_demo():
    print("\n=== DAY 3 DEMO ===\n")

    bank = Bank()

    # Клиенты
    c1 = Client("Timofey", "1", 25, "phone")
    c2 = Client("Alex", "2", 30, "email")

    bank.add_client(c1)
    bank.add_client(c2)

    # Счета
    acc1 = BankAccount("Timofey", Currency.USD)
    acc2 = PremiumAccount("Alex", Currency.EUR, 500, 10)

    bank.open_account("1", acc1)
    bank.open_account("2", acc2)

    acc1.deposit(1000)
    acc2.deposit(200)

    # Авторизация
    bank.authenticate_client("1", True)

    # Ошибки входа
    bank.authenticate_client("2", False)
    bank.authenticate_client("2", False)
    bank.authenticate_client("2", False)

    # Баланс
    print("Total balance Timofey:", bank.get_total_balance("1"))

    # Рейтинг
    print("Ranking:", bank.get_clients_ranking())

    # Заморозка
    bank.freeze_account(acc1.get_id())

    try:
        acc1.withdraw(100)
    except AccountFrozenError as e:
        print("Ошибка:", e)


if __name__ == "__main__":
    run_day3_demo()