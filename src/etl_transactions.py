import os, re
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

'''
ETL Script
- Performs the ingestion and cleaning stage of the pipleline.
- Reads raw multi-user credit card transactions from CSV, standardizes key fields
- removes invalid rows and loads clean version into 'transactions_raw'
- Creates a consistent, analysis - ready dataset to compute category weights and personalized CPI

'''

load_dotenv()

engine = create_engine(os.getenv("DB_URL"))


def load_and_store(csv_path: str):

    df = pd.read_csv(csv_path)

    df['date'] = pd.to_datetime(df['trans_date_trans_time'], errors='coerce')
    df['cc_num'] = df['cc_num'].astype(str)
    df['category'] = df['category'].astype(str)
    df['amt'] = pd.to_numeric(df['amt'], errors='coerce')

    df = df.dropna(subset=['date', 'amt'])

    df[['date', 'cc_num', 'category', 'amt']].to_sql('transactions_raw', engine, if_exists='replace', index=False)

    print("Loaded SQL table transactions_raw")

if __name__ == "__main__":
    load_and_store("data/raw/credit_card_transactions.csv")



