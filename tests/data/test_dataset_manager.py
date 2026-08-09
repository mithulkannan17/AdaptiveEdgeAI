"""
Test Dataset Manager
"""

from managers.dataset_manager import DatasetManager
from utils.dataset_validator import DatasetValidator

manager = DatasetManager()

df = manager.build()

DatasetValidator.validate(df)

df.to_csv(

    "database/raw_metadata.csv",

    index=False

)

print(df.head())