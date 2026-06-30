import pandas as pd


class DatasetService:

    def __init__(self):
        self.df = pd.read_csv("data/churn_dataset.csv")

    def get_preview(self, rows: int = 5):
        return self.df.head(rows)

    def get_info(self):
        return {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "features": self.df.columns.tolist(),
            "churn_distribution": self.df["churn"].value_counts().to_dict()
        }