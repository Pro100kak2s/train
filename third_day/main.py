import datetime

from first_day.main import AccountFrozenError, InvalidOperationError, AccountStatus, Currency, BankAccount
from second_day.main import PremiumAccount


# CLIENT

class Client:
    def __init__(self, full_name, client_id, age, contacts):
        if age < 18:
            raise InvalidOperationError("Клиент должен быть старше 18")

        self.full_name = full_name
        self.client_id = client_id
        self.age = age
        self.contacts = contacts

        self.accounts = []  # список счетов
        self.is_blocked = False
        self.failed_attempts = 0

    def add_account(self, account):
        self.accounts.append(account)

    def __str__(self):
        return f"{self.full_name} (ID: {self.client_id}) | Accounts: {len(self.accounts)}"


# BANK

class Bank:
    def __init__(self):
        self.clients = {}
        self.accounts = {}
    # Добавление клиента
    def add_client(self, client: Client):
        self.clients[client.client_id] = client

    # Открытие счета
    def open_account(self, client_id, account):
        client = self.clients.get(client_id)

        if not client:
            raise InvalidOperationError("Клиент не найден")

        client.add_account(account)
        self.accounts[account.get_id()] = account

    # Закрытие счета
    def close_account(self, account_id):
        account = self.accounts.get(account_id)

        if not account:
            raise InvalidOperationError("Счет не найден")

        account.close()

    # Заморозка
    def freeze_account(self, account_id):
        account = self.accounts.get(account_id)
        account.freeze()

    def unfreeze_account(self, account_id):
        account = self.accounts.get(account_id)

        if account.get_status() == AccountStatus.FROZEN:
            account._status = AccountStatus.ACTIVE

    # Аутентификация
    def authenticate_client(self, client_id, password_correct: bool):
        client = self.clients.get(client_id)

        if not client:
            raise InvalidOperationError("Клиент не найден")

        if client.is_blocked:
            raise InvalidOperationError("Клиент заблокирован")

        if not password_correct:
            client.failed_attempts += 1

            if client.failed_attempts >= 3:
                client.is_blocked = True
                print("Клиент заблокирован из-за попыток входа")

            return False

        client.failed_attempts = 0
        return True

    # Поиск счетов
    def search_accounts(self, client_id):
        client = self.clients.get(client_id)

        if not client:
            return []

        return client.accounts

    # Ночное ограничение
    def check_time_restriction(self):
        hour = datetime.datetime.now().hour

        if 0 <= hour < 5:
            raise InvalidOperationError("Операции запрещены ночью")

    # Общий баланс клиента
    def get_total_balance(self, client_id):
        client = self.clients.get(client_id)

        total = 0
        for acc in client.accounts:
            total += acc.get_balance()

        return total

    # Рейтинг клиентов
    def get_clients_ranking(self):
        ranking = []

        for client in self.clients.values():
            total = sum(acc.get_balance() for acc in client.accounts)
            ranking.append((client.full_name, total))

        return sorted(ranking, key=lambda x: x[1], reverse=True)

# DEMO DAY 3
def run_day3_demo():
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

    # Аутентификация
    print("Auth:", bank.authenticate_client("1", True))

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