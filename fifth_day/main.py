# oop/fifth_day/main.py

import time
from enum import Enum

from oop.fourth_day.main import (
    Transaction,
    TransactionType,
    TransactionProcessor,
    TransactionQueue,
    TransactionStatus
)

from oop.first_day.main import Currency, BankAccount
from oop.second_day.main import PremiumAccount


# =========================================================
# УРОВНИ ЛОГОВ
# =========================================================

class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# =========================================================
# AUDIT LOG
# =========================================================

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

        # сохраняем в память
        self.logs.append(entry)

        # сохраняем в файл
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(f"{entry}\n")

        # выводим в консоль
        print(entry)

    def filter(self, level: LogLevel):
        return [log for log in self.logs if log["level"] == level.value]

    def get_all(self):
        return self.logs


# =========================================================
# УРОВНИ РИСКА
# =========================================================

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# =========================================================
# RISK ANALYZER
# =========================================================

class RiskAnalyzer:

    def __init__(self):
        # история операций по отправителю
        self.history = {}

        # получатели по отправителю (ВАЖНО!)
        self.receivers = {}

    def analyze(self, transaction):
        score = 0
        reasons = []

        # идентификатор отправителя
        sender_id = id(transaction.sender)

        # инициализация
        self.history.setdefault(sender_id, [])
        self.receivers.setdefault(sender_id, set())

        now = time.time()

        # сохраняем операцию
        self.history[sender_id].append(now)

        # =========================
        # 1. КРУПНАЯ СУММА
        # =========================
        if transaction.amount > 1000:
            score += 2
            reasons.append("large_amount")

        # =========================
        # 2. ЧАСТЫЕ ОПЕРАЦИИ
        # =========================
        recent_operations = [
            t for t in self.history[sender_id]
            if now - t < 10
        ]

        if len(recent_operations) > 3:
            score += 2
            reasons.append("too_frequent")

        # =========================
        # 3. НОВЫЙ ПОЛУЧАТЕЛЬ (ВАЖНО!)
        # =========================
        if transaction.receiver:
            receiver_id = id(transaction.receiver)

            if receiver_id not in self.receivers[sender_id]:
                score += 1
                reasons.append("new_receiver")

                # сохраняем
                self.receivers[sender_id].add(receiver_id)

        # =========================
        # 4. НОЧЬ
        # =========================
        hour = time.localtime().tm_hour

        if 0 <= hour < 5:
            score += 2
            reasons.append("night_operation")

        # =========================
        # ОПРЕДЕЛЕНИЕ УРОВНЯ
        # =========================
        if score >= 4:
            level = RiskLevel.HIGH
        elif score >= 2:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        return level, reasons


# =========================================================
# SECURE PROCESSOR
# =========================================================

class SecureTransactionProcessor:

    def __init__(self, base_processor, audit_log, risk_analyzer):
        self.base = base_processor
        self.audit = audit_log
        self.risk = risk_analyzer

    def process(self, transaction):

        # анализ риска
        level, reasons = self.risk.analyze(transaction)

        # логируем ВСЕ операции
        self.audit.log(
            LogLevel.INFO,
            f"TX {transaction.id} risk={level.value} reasons={reasons}"
        )

        # =========================
        # БЛОКИРОВКА
        # =========================
        if level == RiskLevel.HIGH:
            transaction.status = TransactionStatus.BLOCKED
            transaction.error = "Blocked by risk system"

            self.audit.log(
                LogLevel.ERROR,
                f"BLOCKED TX {transaction.id}"
            )
            return

        # =========================
        # ОБЫЧНАЯ ОБРАБОТКА
        # =========================
        self.base.process(transaction)

        # если ошибка — логируем
        if transaction.error:
            self.audit.log(
                LogLevel.ERROR,
                f"ERROR: {transaction.error}"
            )


# =========================================================
# ОТЧЁТЫ
# =========================================================

class AuditReport:

    def __init__(self, audit_log):
        self.audit = audit_log

    # подозрительные операции
    def suspicious_operations(self):
        return self.audit.filter(LogLevel.ERROR)

    # статистика
    def stats(self):
        total = len(self.audit.logs)
        errors = len(self.audit.filter(LogLevel.ERROR))

        return {
            "total_logs": total,
            "error_logs": errors
        }

    # риск профиль (простая версия)
    def risk_summary(self):
        summary = {
            "INFO": len(self.audit.filter(LogLevel.INFO)),
            "ERROR": len(self.audit.filter(LogLevel.ERROR))
        }
        return summary


# =========================================================
# DEMO DAY 5
# =========================================================

def run_day5_demo():
    print("\n=== DAY 5 DEMO ===\n")

    # счета
    acc1 = BankAccount("Timofey", Currency.USD)
    acc2 = PremiumAccount("Alex", Currency.USD, 500, 5)

    acc1.deposit(5000)
    acc2.deposit(100)

    # очередь
    queue = TransactionQueue()

    # процессоры
    base_processor = TransactionProcessor()
    audit = AuditLog()
    risk = RiskAnalyzer()

    processor = SecureTransactionProcessor(base_processor, audit, risk)

    # =========================
    # ТРАНЗАКЦИИ
    # =========================

    # нормальная
    queue.add(Transaction(
        TransactionType.TRANSFER,
        100,
        Currency.USD,
        sender=acc1,
        receiver=acc2,
        fee=2
    ))

    # большая сумма (риск)
    queue.add(Transaction(
        TransactionType.TRANSFER,
        3000,
        Currency.USD,
        sender=acc1,
        receiver=acc2,
        fee=2
    ))

    # частые операции
    for _ in range(5):
        queue.add(Transaction(
            TransactionType.TRANSFER,
            50,
            Currency.USD,
            sender=acc1,
            receiver=acc2,
            fee=1
        ))

    # =========================
    # ОБРАБОТКА
    # =========================

    while True:
        item = queue.get_next()
        if not item:
            break

        tx = item["transaction"]

        processor.process(tx)

        if tx.status == TransactionStatus.PENDING:
            continue

        queue.remove(item)

        if tx.status == TransactionStatus.BLOCKED:
            print("BLOCKED:", tx)
        else:
            print("DONE:", tx)

    # =========================
    # ОТЧЁТ
    # =========================

    report = AuditReport(audit)

    print("\n=== AUDIT REPORT ===")
    print("Stats:", report.stats())
    print("Suspicious:", report.suspicious_operations())


# =========================================================
# ЗАПУСК
# =========================================================

if __name__ == "__main__":
    run_day5_demo()