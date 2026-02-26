import pandas as pd
from datetime import datetime
from sqlalchemy import text
from abc import ABC, abstractmethod
from save_database import DeleteData, UpdateDataSQL


# Filter a DataFrame based on a date range for a specific column
def filter_data(data, column, start_date, end_date):
    data_cpy = data.copy()

    # Convert the column to numeric, safely handle errors, and use nullable Int64
    data_cpy[column] = pd.to_numeric(data_cpy[column], errors="coerce").astype("Int64")

    # Filter rows where column is within the start_date (exclusive) and end_date (inclusive)
    filter_df = data_cpy[(data_cpy[column] <= end_date) & (data_cpy[column] > start_date)].copy()

    return filter_df


# Create a hash column by concatenating two columns
def create_hash(data, col1, col2):
    data_cpy = data.copy()
    data_cpy['hash'] = (
            data_cpy[col1].astype(str) +
            data_cpy[col2].astype(str).str.replace("-", "", regex=True)  # Remove hyphens
    )

    return data_cpy


# Class to remove extra rows from the database that do not exist in view data
class RemoveExtraRows:

    def __init__(self, table_name: str):
        self.table_name = table_name

    def remove_extra_rows(self, extra_ids, remove_obj: DeleteData, connection) -> None:


        # Delete extra rows using the DeleteDataSQL object
        remove_obj.delete(self.table_name, connection, extra_ids, "ID")


class ExtraFinder:

    def __init__(self, data: pd.DataFrame, table_name: str, date_now: datetime):
        
        self.database_data = data
        self.table_name = table_name
        self.date_now = date_now

    def extra_row_finder(self, vw_data: pd.DataFrame) -> pd.DataFrame:
        # Filter database rows within the given date range
        database_data = filter_data(self.database_data, 'Tarikh_komaki', 14040101, self.date_now)

        database_data_cpy = database_data.copy()
        view_data_cpy = vw_data.copy()

        # Ensure IDs are of type Int64 for safe comparison
        database_data_cpy['ID'] = database_data_cpy['ID'].astype("Int64")
        view_data_cpy['ID'] = view_data_cpy['ID'].astype("Int64")

        # Find IDs that exist in the database but not in the view → candidates for deletion
        extra_ids = pd.DataFrame(
            database_data_cpy.loc[~database_data_cpy['ID'].isin(view_data_cpy['ID']), 'ID'].unique(), columns=['ID'])

        return extra_ids


# Abstract base class for checking hashes
class CheckHash(ABC):

    @abstractmethod
    def check(self, data: pd.DataFrame, end_date: int) -> tuple[list[int], list[int]]:
        pass


# Abstract base class for creating hashes
class CreateHash(ABC):

    @abstractmethod
    def create_hash(self, data: pd.DataFrame) -> pd.DataFrame:
        pass


# Concrete implementation to create hash for sales data
class CreateHashSell(CreateHash):

    def __init__(self, date_now):
        self.date_now = date_now

    def create_hash(self, data: pd.DataFrame):
        data_cpy = data.copy()

        # Create a DataFrame with ID, concatenated hash, and the current date
#################
        hash_df = pd.DataFrame({
            "ID": data_cpy["ID"],
            "hash": (
                    data_cpy["ID"].astype(str)
                    + data_cpy["netvalue"].astype("Int64").astype(str).str.replace("-", "", regex=False)
            ),
            "DateUpdate": self.date_now
        })

        return hash_df


# Concrete implementation to check hashes for sales data
class CheckHashSell(CheckHash):

    def __init__(self, hash_data: pd.DataFrame):
        self.hash_table = hash_data.copy()

    def check(self, data: pd.DataFrame, end_date: int, start_date: int = 14040101):
        # Filter input data based on the date range
        data_cpy = filter_data(data, 'Tarikh_komaki', start_date, end_date)

        # Ensure ID is numeric and hash is string for comparison
        data_cpy["ID"] = pd.to_numeric(data_cpy["ID"], errors="coerce").astype("Int64")
        data_cpy["hash"] = data_cpy["hash"].astype(str)

        # Prepare the hash table for merging
        hash_table = self.hash_table.copy()
        hash_table["ID"] = pd.to_numeric(hash_table["ID"], errors="coerce").astype("Int64")
        hash_table["hash"] = hash_table["hash"].astype(str)

        # Merge input data with existing hash table on ID
        merged = data_cpy.merge(
            hash_table,
            on="ID",
            how="left",
            suffixes=("", "_db")
        )

        # Rows where ID exists but hash differs → update
        row_update = merged[
            (merged["hash_db"].notna()) &
            (merged["hash"] != merged["hash_db"])
            ]["ID"].tolist()

        # Rows where ID does not exist in hash table → create
        row_create = merged[
            merged["hash_db"].isna()
        ]["ID"].tolist()

        return row_update, row_create


# Abstract base class for updating hashes in database
class UpdateHash(ABC):

    @abstractmethod
    def update_hash(self, data: pd.DataFrame, list_id: list, update_obj: UpdateDataSQL, connection) -> None:
        pass


# Concrete implementation to update sales hashes in the database
class UpdateHashSell(UpdateHash):

    def __init__(self, date_now):
        self.date_now = date_now

    def update_hash(self, data: pd.DataFrame, list_id: list, update_obj: UpdateDataSQL, connection) -> None:
        # Filter data to only include IDs that need updating

##############
        data_cpy = data[data['ID'].isin(list_id)].copy()

        # Prepare DataFrame with ID, hash, and update date
        hash_data = pd.DataFrame({
            "ID": data_cpy["ID"],
            "hash": data_cpy["hash"],
            "DateUpdate": self.date_now
        })

        # Perform bulk update in the database
        update_obj.update_data(table='Fact_Hash', data=hash_data, connection=connection, key_column='ID')
