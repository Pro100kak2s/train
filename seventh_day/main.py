import json
import csv
import matplotlib.pyplot as plt

from first_day.main import BankAccount, Currency


# =========================================================
# REPORT BUILDER
# =========================================================

class ReportBuilder:

    # JSON
    def export_to_json(self, data, filename):
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    # CSV
    def export_to_csv(self, data, filename):
        if not data:
            return

        keys = data[0].keys()

        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)

    # BAR CHART
    def build_bar_chart(self, labels, values, filename):
        plt.figure()
        plt.bar(labels, values)
        plt.title("Balances")
        plt.savefig(filename)
        plt.close()

    # PIE CHART
    def build_pie_chart(self, labels, values, filename):
        plt.figure()
        plt.pie(values, labels=labels, autopct='%1.1f%%')
        plt.title("Distribution")
        plt.savefig(filename)
        plt.close()

    # LINE CHART
    def build_line_chart(self, values, filename):
        plt.figure()
        plt.plot(values)
        plt.title("Balance History")
        plt.savefig(filename)
        plt.close()


# =========================================================
# DEMO
# =========================================================

def run_day7_demo():
    print("\n=== DAY 7 DEMO ===\n")

    builder = ReportBuilder()

    # создаем счета
    acc1 = BankAccount("Timofey", Currency.USD)
    acc2 = BankAccount("Alex", Currency.EUR)

    acc1.deposit(1000)
    acc1.withdraw(200)

    acc2.deposit(500)

    accounts = [acc1, acc2]

    # =========================
    # DATA
    # =========================

    data = [acc.get_account_info() for acc in accounts]

    print("DATA:", data)

    # =========================
    # EXPORT
    # =========================

    builder.export_to_json(data, "report.json")
    builder.export_to_csv(data, "report.csv")

    # =========================
    # CHARTS
    # =========================

    names = [d["owner"] for d in data]
    balances = [d["balance"] for d in data]

    builder.build_bar_chart(names, balances, "bar.png")
    builder.build_pie_chart(names, balances, "pie.png")
    builder.build_line_chart(balances, "line.png")

    print("\nФайлы созданы:")
    print("report.json")
    print("report.csv")
    print("bar.png")
    print("pie.png")
    print("line.png")


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    run_day7_demo()