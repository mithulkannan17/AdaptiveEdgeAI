from database.dataset_manager import DatasetManager
from utils.dataset_validator import DatasetValidator

manager = DatasetManager()

df = manager.build()

DatasetValidator.validate(df)

print(df.head())

df.to_csv("database/raw_metadata.csv", index=False)