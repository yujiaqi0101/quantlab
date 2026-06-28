import sys
sys.path.insert(0, '.')
import pandas as pd
import os

parquet_dir = 'storage/parquet/datasets'
for f in os.listdir(parquet_dir):
    if f.endswith('.parquet'):
        path = os.path.join(parquet_dir, f)
        try:
            df = pd.read_parquet(path)
            print(f'\n=== {f} ===')
            print(f'  Shape: {df.shape}')
            print(f'  Columns: {list(df.columns)}')
            print(f'  Index: {type(df.index).__name__}')
            if isinstance(df.index, pd.DatetimeIndex):
                print(f'  Date range: {df.index.min()} ~ {df.index.max()}')
            print(f'  Head (3 rows):')
            print(df.head(3).to_string())
            if 'symbol' in df.columns:
                print(f'  Symbols: {df["symbol"].nunique()} unique')
                print(f'  Sample symbols: {df["symbol"].unique()[:5].tolist()}')
        except Exception as e:
            print(f'{f}: ERROR {e}')
