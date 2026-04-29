import random

from oop.third_day.main import Bank, Client
from oop.fourth_day.main import (
    Transaction,
    TransactionType,
    TransactionQueue,
    TransactionProcessor,
    TransactionStatus
)
from oop.fifth_day.main import (
    AuditLog,
    RiskAnalyzer,
    SecureTransactionProcessor,
    LogLevel,
    AuditReport
)

from oop.first_day.main import Currency, BankAccount
from oop.second_day.main import PremiumAccount


# =========================================================
# СОЗДАНИЕ СИСТЕМЫ
# =========================================================

def create_system():
    bank = Bank()

    clients = []
    accounts = []

    print("\n=== CREATE CLIENTS ===")

    # 5 клиентов
    for i in range(5):
        client = Client(f"Client_{i}", str(i), 25 + i, "contact")
        bank.add_client(client)
        clients.append(client)

        print(f"Created client: {client.full_name}")

    print("\n=== CREATE ACCOUNTS ===")

    # 2-3 счета на клиента
    for client in clients:
        for _ in range(random.randint(2, 3)):

            if random.random() > 0.5:
                acc = BankAccount(client.full_name, Currency.USD)
            else:
                acc = PremiumAccount(client.full_name, Currency.USD, 500, 5)

            # начальный баланс
            acc.deposit(random.randint(500, 3000))

            bank.open_account(client.client_id, acc)
            accounts.append(acc)

            print("Account:", acc)

    return bank, clients, accounts


# =========================================================
# СИМУЛЯЦИЯ ТРАНЗАКЦИЙ
# =========================================================

def simulate_transactions(accounts):

    queue = TransactionQueue()

    base_processor = TransactionProcessor()
    audit = AuditLog()
    risk = RiskAnalyzer()

    processor = SecureTransactionProcessor(base_processor, audit, risk)

    print("\n=== ADD TRANSACTIONS TO QUEUE ===")

    # =====================================================
    # 1. НОРМАЛЬНЫЕ
    # =====================================================
    for _ in range(20):
        sender = random.choice(accounts)
        receiver = random.choice(accounts)

        tx = Transaction(
            TransactionType.TRANSFER,
            amount=random.randint(50, 500),
            currency=Currency.USD,
            sender=sender,
            receiver=receiver,
            fee=2
        )

        queue.add(tx, priority=random.randint(0, 2))
        print("QUEUE NORMAL:", tx)

    # =====================================================
    # 2. ОШИБОЧНЫЕ (недостаточно средств)
    # =====================================================
    for _ in range(10):
        sender = random.choice(accounts)
        receiver = random.choice(accounts)

        tx = Transaction(
            TransactionType.TRANSFER,
            amount=999999,  # точно ошибка
            currency=Currency.USD,
            sender=sender,
            receiver=receiver,
            fee=5
        )

        queue.add(tx)
        print("QUEUE ERROR:", tx)

    # =====================================================
    # 3. ПОДОЗРИТЕЛЬНЫЕ (большие суммы)
    # =====================================================
    for _ in range(10):
        sender = random.choice(accounts)
        receiver = random.choice(accounts)

        tx = Transaction(
            TransactionType.TRANSFER,
            amount=3000,  # риск
            currency=Currency.USD,
            sender=sender,
            receiver=receiver,
            fee=3
        )

        queue.add(tx)
        print("QUEUE RISK:", tx)

    # =====================================================
    # ОБРАБОТКА
    # =====================================================

    print("\n=== PROCESSING ===")

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

        if tx.status == TransactionStatus.BLOCKED:
            print("BLOCKED:", tx)
        elif tx.status == TransactionStatus.FAILED:
            print("FAILED:", tx)
        else:
            print("SUCCESS:", tx)

    return results, audit


# =========================================================
# USER СЦЕНАРИИ
# =========================================================

def user_scenarios(bank, clients):
    print("\n=== USER SCENARIOS ===")

    client = random.choice(clients)

    print("CLIENT:", client.full_name)

    accounts = bank.search_accounts(client.client_id)

    print("\nACCOUNTS:")
    for acc in accounts:
        print(acc)

    print("\nTOTAL BALANCE:", bank.get_total_balance(client.client_id))


# =========================================================
# ОТЧЁТЫ
# =========================================================

def show_reports(bank, clients, results, audit):

    print("\n=== REPORTS ===")

    # =========================
    # ТОП КЛИЕНТОВ
    # =========================
    print("\nTOP 3 CLIENTS:")
    ranking = bank.get_clients_ranking()

    for name, balance in ranking[:3]:
        print(name, "->", balance)

    # =========================
    # СТАТИСТИКА ТРАНЗАКЦИЙ
    # =========================
    success = len([t for t in results if t.status == TransactionStatus.SUCCESS])
    failed = len([t for t in results if t.status == TransactionStatus.FAILED])
    blocked = len([t for t in results if t.status == TransactionStatus.BLOCKED])

    print("\nTRANSACTIONS:")
    print("SUCCESS:", success)
    print("FAILED:", failed)
    print("BLOCKED:", blocked)

    # =========================
    # ОБЩИЙ БАЛАНС
    # =========================
    total = sum(bank.get_total_balance(c.client_id) for c in clients)

    print("\nTOTAL BANK BALANCE:", total)

    # =========================
    # ПОДОЗРИТЕЛЬНЫЕ
    # =========================
    print("\nSUSPICIOUS OPERATIONS:")

    for log in audit.filter(LogLevel.ERROR):
        print(log)

    # =========================
    # AUDIT REPORT
    # =========================
    report = AuditReport(audit)

    print("\nAUDIT STATS:", report.stats())


# =========================================================
# MAIN
# =========================================================

def run_day6_demo():
    print("\n========== DAY 6 ==========\n")

    bank, clients, accounts = create_system()

    results, audit = simulate_transactions(accounts)

    user_scenarios(bank, clients)

    show_reports(bank, clients, results, audit)


# ЗАПУСК

if __name__ == "__main__":
    run_day6_demo()