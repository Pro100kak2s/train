from first_day.main import Currency, InsufficientFundsError, BankAccount, InvalidOperationError


class SavingsAccount(BankAccount):
    def __init__(self, owner, currency, min_balance, interest_rate, account_id=None):
        super().__init__(owner, currency, account_id)

        self._min_balance = min_balance
        self._interest_rate = interest_rate  # например 0.05 = 5%

    def withdraw(self, amount: float):
        self._ensure_active()
        self._validate_amount(amount)

        if self._balance - amount < self._min_balance:
            raise InsufficientFundsError("Нельзя нарушить минимальный остаток")

        self._balance -= amount

    def apply_monthly_interest(self):
        interest = self._balance * (self._interest_rate / 12)
        self._balance += interest

    def get_account_info(self):
        base = super().get_account_info()
        base.update({
            "type": "SavingsAccount",
            "min_balance": self._min_balance,
            "interest_rate": self._interest_rate
        })
        return base

    def __str__(self):
        return super().__str__() + f" | MinBalance: {self._min_balance}"

# PREMIUM ACCOUNT

class PremiumAccount(BankAccount):
    def __init__(self, owner, currency, overdraft_limit, fee, account_id=None):
        super().__init__(owner, currency, account_id)
        self._overdraft_limit = overdraft_limit
        self._fee = fee

    def withdraw(self, amount: float):
        self._ensure_active()
        self._validate_amount(amount)

        total = amount + self._fee

        if self._balance - total < -self._overdraft_limit:
            raise InsufficientFundsError("Превышен лимит овердрафта")

        self._balance -= total

    def get_account_info(self):
        base = super().get_account_info()
        base.update({
            "type": "PremiumAccount",
            "overdraft_limit": self._overdraft_limit,
            "fee": self._fee
        })
        return base

    def __str__(self):
        return super().__str__() + f" | Overdraft: {self._overdraft_limit}"

# INVESTMENT ACCOUNT

class InvestmentAccount(BankAccount):
    def __init__(self, owner, currency, account_id=None):
        super().__init__(owner, currency, account_id)

        self._portfolio = {
            "stocks": 0,
            "bonds": 0,
            "etf": 0
        }

    def invest(self, asset_type, amount):
        self._ensure_active()
        self._validate_amount(amount)

        if asset_type not in self._portfolio:
            raise InvalidOperationError("Неизвестный актив")

        if amount > self._balance:
            raise InsufficientFundsError("Недостаточно средств")

        self._portfolio[asset_type] += amount
        self._balance -= amount

    def project_yearly_growth(self):
        growth_rates = {
            "stocks": 0.10,
            "bonds": 0.05,
            "etf": 0.07
        }

        total = 0
        for asset, value in self._portfolio.items():
            total += value * (1 + growth_rates[asset])

        return round(total, 2)

    def withdraw(self, amount: float):
        self._ensure_active()
        self._validate_amount(amount)

        if amount > self._balance:
            raise InsufficientFundsError("Недостаточно ликвидных средств")

        self._balance -= amount

    def get_account_info(self):
        base = super().get_account_info()
        base.update({
            "type": "InvestmentAccount",
            "portfolio": self._portfolio
        })
        return base

    def __str__(self):
        return super().__str__() + f" | Portfolio: {self._portfolio}"


# DEMO DAY 2

def run_day2_demo():
    print("\n=== DAY 2 DEMO ===\n")

    # SavingsAccount
    s = SavingsAccount("Timofey", Currency.USD, min_balance=100, interest_rate=0.06)
    s.deposit(1000)
    s.apply_monthly_interest()
    print("Savings:", s)

    # PremiumAccount
    p = PremiumAccount("Alex", Currency.EUR, overdraft_limit=500, fee=10)
    p.deposit(200)
    p.withdraw(600)
    print("Premium:", p)

    # InvestmentAccount
    i = InvestmentAccount("John", Currency.USD)
    i.deposit(2000)
    i.invest("stocks", 1000)
    i.invest("bonds", 500)

    print("Investment:", i)
    print("Projected growth:", i.project_yearly_growth())


if __name__ == "__main__":
    run_day2_demo()