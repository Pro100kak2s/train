import random

from third_day.main import Bank, Client
from fourth_day.main import (
    Transaction,
    TransactionType,
    TransactionQueue,
    TransactionProcessor,
    TransactionStatus
)
from fifth_day.main import (
    AuditLog,
    RiskAnalyzer,
    SecureTransactionProcessor,
    LogLevel
)

from first_day.main import Currency, BankAccount
from second_day.main import PremiumAccount


# =========================
# СОЗДАНИЕ СИСТЕМЫ
# =========================

def create_system():
    bank = Bank()

    clients = []
    accounts = []

    # создаем клиентов
    for i in range(5):
        client = Client(f"Client_{i}", str(i), 25 + i, "contact")
        bank.add_client(client)
        clients.append(client)

    # создаем счета
    for client in clients:
        for _ in range(random.randint(2, 3)):
            if random.random() > 0.5:
                acc = BankAccount(client.full_name, Currency.USD)
            else:
                acc = PremiumAccount(client.full_name, Currency.USD, 500, 5)

            acc.deposit(random.randint(500, 3000))

            bank.open_account(client.client_id, acc)
            accounts.append(acc)

    return bank, clients, accounts


# =========================
# СИМУЛЯЦИЯ ТРАНЗАКЦИЙ
# =========================

def simulate_transactions(accounts):
    queue = TransactionQueue()
    base_processor = TransactionProcessor()

    audit = AuditLog()
    risk = RiskAnalyzer()

    processor = SecureTransactionProcessor(base_processor, audit, risk)

    # создаем 40 транзакций
    for _ in range(40):
        sender = random.choice(accounts)
        receiver = random.choice(accounts)

        amount = random.randint(50, 3000)

        t = Transaction(
            TransactionType.TRANSFER,
            amount=amount,
            currency=Currency.USD,
            sender=sender,
            receiver=receiver,
            fee=random.randint(1, 5)
        )

        queue.add(t, priority=random.randint(0, 3))

        print("QUEUE:", t)

    # обработка
    results = []

    while True:
        item = queue.get_next()
        if not item:
            break

        tx = item["transaction"]

        processor.process(tx)

        if tx.status == TransactionStatus.PENDING:
            continue

        queue.remove(item)
        results.append(tx)

        print("PROCESSED:", tx)

    return results, audit

# =========================
# ОТЧЁТЫ
# =========================

def show_reports(bank, clients, results, audit):
    print("\n=== REPORTS ===\n")

    # топ клиенты
    ranking = bank.get_clients_ranking()
    print("TOP 3 CLIENTS:")
    for r in ranking[:3]:
        print(r)

    # статистика транзакций
    success = len([t for t in results if t.status == TransactionStatus.SUCCESS])
    failed = len([t for t in results if t.status == TransactionStatus.FAILED])
    blocked = len([t for t in results if t.status == TransactionStatus.BLOCKED])

    print("\nTRANSACTION STATS:")
    print("SUCCESS:", success)
    print("FAILED:", failed)
    print("BLOCKED:", blocked)

    # общий баланс
    total = 0
    for client in clients:
        total += bank.get_total_balance(client.client_id)

    print("\nTOTAL BANK BALANCE:", total)

    # подозрительные операции
    print("\nSUSPICIOUS OPERATIONS:")
    for log in audit.filter(LogLevel.ERROR):
        print(log)


# =========================
# СЦЕНАРИИ ПОЛЬЗОВАТЕЛЯ
# =========================

def user_scenarios(bank, clients):
    print("\n=== USER SCENARIOS ===\n")

    client = random.choice(clients)

    print("CLIENT:", client.full_name)

    accounts = bank.search_accounts(client.client_id)

    print("ACCOUNTS:")
    for acc in accounts:
        print(acc)

    print("TOTAL BALANCE:", bank.get_total_balance(client.client_id))


# =========================
# MAIN
# =========================

def run_day6_demo():
    print("\n=== DAY 6 DEMO ===\n")

    bank, clients, accounts = create_system()

    results, audit = simulate_transactions(accounts)

    user_scenarios(bank, clients)

    show_reports(bank, clients, results, audit)


if __name__ == "__main__":
    run_day6_demo()