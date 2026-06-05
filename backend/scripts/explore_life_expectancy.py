import pandas as pd
import kagglehub

path = kagglehub.dataset_download(
    "kumarajarshi/life-expectancy-who"
)

csv_path = (
    path +
    "\\Life Expectancy Data.csv"
)

df = pd.read_csv(csv_path)

print("\n===== SHAPE =====")
print(df.shape)

print("\n===== COLUMNS =====")
print(df.columns.tolist())

print("\n===== INFO =====")
print(df.info())

print("\n===== FIRST 5 ROWS =====")
print(df.head())

print("\n===== MISSING VALUES =====")
print(df.isnull().sum())