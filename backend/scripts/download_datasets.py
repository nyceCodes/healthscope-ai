import kagglehub
import os

print("Downloading WHO Life Expectancy Dataset...")

path = kagglehub.dataset_download(
    "kumarajarshi/life-expectancy-who"
)

print("\nDataset Path:")
print(path)

print("\nFiles Found:")

for root, dirs, files in os.walk(path):
    for file in files:
        print(os.path.join(root, file))