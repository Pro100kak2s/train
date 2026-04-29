# oop/seventh_day/main.py

import json
import csv
import os
import matplotlib.pyplot as plt

from oop.first_day.main import BankAccount, Currency
from oop.fourth_day.main import TransactionStatus


# =========================================================
# REPORT BUILDER
# =========================================================

class ReportBuilder:

    # =========================
    # CLIENT REPORT
    # =========================
    def build_client_report(self, client_name, accounts):
        return {
            "client": client_name,
            "accounts": [a.get_account_info() for a in accounts],
            "total_balance": sum(a.get_balance() for a in accounts)
        }

    # =========================
    # BANK REPORT
    # =========================
    def build_bank_report(self, accounts):
        return {
            "total_balance": sum(a.get_balance() for a in accounts),
            "accounts_count": len(accounts),
            "avg_balance": (
                sum(a.get_balance() for a in accounts) / len(accounts)
                if accounts else 0
            )
        }

    # =========================
    # RISK REPORT
    # =========================
    def build_risk_report(self, transactions):
        return {
            "blocked": len([t for t in transactions if t.status == TransactionStatus.BLOCKED]),
            "failed": len([t for t in transactions if t.status == TransactionStatus.FAILED]),
            "success": len([t for t in transactions if t.status == TransactionStatus.SUCCESS]),
        }

    # =====================================================
    # EXPORT
    # =====================================================

    def export_to_json(self, data, filename):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def export_to_csv(self, data, filename):
        if not data:
            return

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    # =====================================================
    # CHARTS
    # =====================================================

    def build_bar_chart(self, labels, values, filename):
        plt.figure()
        plt.bar(labels, values)
        plt.title("Balances")
        plt.xlabel("Clients")
        plt.ylabel("Balance")
        plt.savefig(filename)
        plt.close()

    def build_pie_chart(self, labels, values, filename):
        plt.figure()
        plt.pie(values, labels=labels, autopct="%1.1f%%")
        plt.title("Balance Distribution")
        plt.savefig(filename)
        plt.close()

    def build_line_chart(self, values, filename):
        plt.figure()
        plt.plot(values)
        plt.title("Balance Trend")
        plt.xlabel("Step")
        plt.ylabel("Balance")
        plt.savefig(filename)
        plt.close()

    # =====================================================
    # SAVE ALL CHARTS
    # =====================================================

    def save_charts(self, accounts, folder="charts"):
        os.makedirs(folder, exist_ok=True)

        names = [a.get_account_info()["owner"] for a in accounts]
        balances = [a.get_balance() for a in accounts]

        self.build_bar_chart(names, balances, f"{folder}/bar.png")
        self.build_pie_chart(names, balances, f"{folder}/pie.png")
        self.build_line_chart(balances, f"{folder}/line.png")


# =========================================================
# DEMO
# =========================================================

def run_day7_demo():
    print("\n DAY 7 \n")

    builder = ReportBuilder()

    # =========================
    # ДАННЫЕ
    # =========================

    acc1 = BankAccount("Timofey", Currency.USD)
    acc2 = BankAccount("Alex", Currency.EUR)
    acc3 = BankAccount("John", Currency.USD)

    acc1.deposit(1000)
    acc1.withdraw(200)

    acc2.deposit(500)
    acc3.deposit(2000)

    accounts = [acc1, acc2, acc3]

    # фейковые транзакции (для отчета)
    class FakeTx:
        def __init__(self, status):
            self.status = status

    transactions = [
        FakeTx(TransactionStatus.SUCCESS),
        FakeTx(TransactionStatus.SUCCESS),
        FakeTx(TransactionStatus.FAILED),
        FakeTx(TransactionStatus.BLOCKED),
        FakeTx(TransactionStatus.BLOCKED),
    ]

    # =========================
    # REPORTS
    # =========================

    client_report = builder.build_client_report("Timofey", [acc1])
    bank_report = builder.build_bank_report(accounts)
    risk_report = builder.build_risk_report(transactions)

    print("CLIENT REPORT:", client_report)
    print("BANK REPORT:", bank_report)
    print("RISK REPORT:", risk_report)

    # =========================
    # EXPORT
    # =========================

    builder.export_to_json(client_report, "client_report.json")
    builder.export_to_json(bank_report, "bank_report.json")
    builder.export_to_json(risk_report, "risk_report.json")

    builder.export_to_csv(
        [a.get_account_info() for a in accounts],
        "accounts.csv"
    )

    # CHARTS

    builder.save_charts(accounts)

    print("\n Файлы созданы:")
    print("- client_report.json")
    print("- bank_report.json")
    print("- risk_report.json")
    print("- accounts.csv")
    print("- charts/bar.png")
    print("- charts/pie.png")
    print("- charts/line.png")


# START

if __name__ == "__main__":
    run_day7_demo()