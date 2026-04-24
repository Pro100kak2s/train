import time
from enum import Enum

from fourth_day.main import (
    Transaction,
    TransactionType,
    TransactionProcessor,
    TransactionQueue,
    TransactionStatus
)

from first_day.main import Currency, BankAccount
from second_day.main import PremiumAccount


# =========================
# УРОВНИ ВАЖНОСТИ
# =========================

class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# =========================
# AUDIT LOG
# =========================

class AuditLog:
    def __init__(self, file_path="audit.log"):
        self.logs = []
        self.file_path = file_path

    def log(self, level: LogLevel, message: str):
        entry = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": level.value,
            "message": message
        }

        self.logs.append(entry)

        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(f"{entry}\n")

        print(entry)

    def filter(self, level: LogLevel):
        return [log for log in self.logs if log["level"] == level.value]

    def get_all(self):
        return self.logs


# =========================
# RISK ANALYZER
# =========================

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskAnalyzer:
    def __init__(self):
        self.history = {}
        self.receivers = set()  # фикс new_receiver

    def analyze(self, transaction):
        score = 0
        reasons = []

        # 1. крупная сумма
        if transaction.amount > 1000:
            score += 2
            reasons.append("large_amount")

        # 2. частые операции
        if transaction.sender:
            sender_id = id(transaction.sender)

            self.history.setdefault(sender_id, [])

            now = time.time()
            self.history[sender_id].append(now)

            recent = [t for t in self.history[sender_id] if now - t < 10]

            if len(recent) > 3:
                score += 2
                reasons.append("too_frequent")

        # 3. новый получатель
        if transaction.receiver:
            rid = id(transaction.receiver)

            if rid not in self.receivers:
                score += 1
                reasons.append("new_receiver")
                self.receivers.add(rid)

        # 4. ночь
        hour = time.localtime().tm_hour
        if 0 <= hour < 5:
            score += 2
            reasons.append("night_operation")

        # итог
        if score >= 4:
            return RiskLevel.HIGH, reasons
        elif score >= 2:
            return RiskLevel.MEDIUM, reasons

        return RiskLevel.LOW, reasons


# =========================
# SECURE PROCESSOR
# =========================

class SecureTransactionProcessor:
    def __init__(self, base_processor, audit_log, risk_analyzer):
        self.base = base_processor
        self.audit = audit_log
        self.risk = risk_analyzer

    def process(self, transaction):
        level, reasons = self.risk.analyze(transaction)

        self.audit.log(
            LogLevel.INFO,
            f"TX {transaction.id} risk={level.value} reasons={reasons}"
        )

        # БЛОКИРОВКА
        if level == RiskLevel.HIGH:
            transaction.status = TransactionStatus.BLOCKED
            transaction.error = "Blocked by risk system"

            self.audit.log(
                LogLevel.ERROR,
                f"BLOCKED TX {transaction.id}"
            )
            return

        # обычная обработка
        self.base.process(transaction)

        if transaction.error:
            self.audit.log(
                LogLevel.ERROR,
                f"ERROR: {transaction.error}"
            )


# =========================
# DEMO DAY 5
# =========================

def run_day5_demo():
    print("\n=== DAY 5 DEMO ===\n")

    acc1 = BankAccount("Timofey", Currency.USD)
    acc2 = PremiumAccount("Alex", Currency.USD, 500, 5)

    acc1.deposit(5000)
    acc2.deposit(100)

    queue = TransactionQueue()
    base_processor = TransactionProcessor()

    audit = AuditLog()
    risk = RiskAnalyzer()

    processor = SecureTransactionProcessor(base_processor, audit, risk)

    # норм
    queue.add(Transaction(
        TransactionType.TRANSFER, 100, Currency.USD,
        sender=acc1, receiver=acc2, fee=2
    ))

    # большая сумма → HIGH риск
    queue.add(Transaction(
        TransactionType.TRANSFER, 3000, Currency.USD,
        sender=acc1, receiver=acc2, fee=2
    ))

    # частые операции
    for _ in range(5):
        queue.add(Transaction(
            TransactionType.TRANSFER, 50, Currency.USD,
            sender=acc1, receiver=acc2, fee=1
        ))

    # обработка
    while True:
        item = queue.get_next()
        if not item:
            break

        tx = item["transaction"]

        processor.process(tx)

        if tx.status == TransactionStatus.BLOCKED:
            queue.remove(item)
            print("BLOCKED:", tx)
            continue

        if tx.status == TransactionStatus.PENDING:
            continue

        queue.remove(item)
        print(tx)

    print("\n=== AUDIT STATS ===")
    print("Errors:", len(audit.filter(LogLevel.ERROR)))


# =========================
# ЗАПУСК
# =========================

if __name__ == "__main__":
    run_day5_demo()