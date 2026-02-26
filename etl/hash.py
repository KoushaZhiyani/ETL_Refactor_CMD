import pandas as pd
from datetime import datetime
from sqlalchemy import text
from abc import ABC, abstractmethod
from save_database import DeleteData, UpdateData


# Filters rows based on an integer-based date range column.
# The column is safely coerced to nullable Int64 before comparison.
def filter_data(data, column, start_date, end_date):
    data_cpy = data.copy()

    # Ensure numeric comparison (invalid values become <NA>)
    data_cpy[column] = pd.to_numeric(
        data_cpy[column], errors="coerce"
    ).astype("Int64")

    # Keep rows where start_date < column <= end_date
    filter_df = data_cpy[
        (data_cpy[column] <= end_date) &
        (data_cpy[column] > start_date)
    ].copy()

    return filter_df


# Generates a deterministic hash column by concatenating two columns.
# Hyphens are removed from the second column before concatenation.
def create_hash(data, col1, col2):
    data_cpy = data.copy()

    data_cpy["hash"] = (
        data_cpy[col1].astype(str) +
        data_cpy[col2].astype(str).str.replace("-", "", regex=True)
    )

    return data_cpy


# Responsible for deleting records from the target table
# that no longer exist in the source view.
class RemoveExtraRows:

    def __init__(self, table_name: str):
        self.table_name = table_name

    def remove_extra_rows(self, extra_ids, remove_obj: DeleteData, connection) -> None:
        # Delegates bulk deletion to the persistence layer
        remove_obj.delete(
            self.table_name,
            connection,
            extra_ids,
            "ID"
        )


class ExtraFinder:
    """
    Identifies records that exist in the database table
    but are missing from the current view dataset.
    These records are considered deletion candidates.
    """

    def __init__(self, data: pd.DataFrame, table_name: str, date_now: datetime):
        self.database_data = data
        self.table_name = table_name
        self.date_now = date_now

    def extra_row_finder(self, vw_data: pd.DataFrame) -> pd.DataFrame:

        # Restrict comparison to rows within the active date window
        database_data = filter_data(
            self.database_data,
            "Tarikh_komaki",
            14040101,
            self.date_now
        )

        database_data_cpy = database_data.copy()
        view_data_cpy = vw_data.copy()

        # Normalize ID types for reliable comparison
        database_data_cpy["ID"] = database_data_cpy["ID"].astype("Int64")
        view_data_cpy["ID"] = view_data_cpy["ID"].astype("Int64")

        # IDs present in DB but missing in view → must be removed
        extra_ids = pd.DataFrame(
            database_data_cpy.loc[
                ~database_data_cpy["ID"].isin(view_data_cpy["ID"]),
                "ID"
            ].unique(),
            columns=["ID"]
        )

        return extra_ids


# Contract for hash comparison strategies.
class CheckHash(ABC):

    @abstractmethod
    def check(self, data: pd.DataFrame, end_date: int) -> tuple[list[int], list[int]]:
        """
        Returns:
            (ids_to_update, ids_to_create)
        """
        pass


# Contract for hash creation strategies.
class CreateHash(ABC):

    @abstractmethod
    def create_hash(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Returns a DataFrame containing:
            ID, hash, DateUpdate
        """
        pass


class CreateHashSell(CreateHash):
    """
    Concrete hash generation strategy for sales records.
    """

    def __init__(self, date_now):
        self.date_now = date_now

    def create_hash(self, data: pd.DataFrame):
        data_cpy = data.copy()

        # Build hash dataset for insertion into Fact_Hash table
        hash_df = pd.DataFrame({
            "ID": data_cpy["ID"],
            "hash": (
                data_cpy["ID"].astype(str) +
                data_cpy["netvalue"]
                .astype("Int64")
                .astype(str)
                .str.replace("-", "", regex=False)
            ),
            "DateUpdate": self.date_now
        })

        return hash_df


class CheckHashSell(CheckHash):
    """
    Compares incoming sales data with existing hash table
    to determine which rows require creation or update.
    """

    def __init__(self, hash_data: pd.DataFrame):
        self.hash_table = hash_data.copy()

    def check(self, data: pd.DataFrame, end_date: int, start_date: int = 14040101):

        # Limit comparison to active date window
        data_cpy = filter_data(
            data,
            "Tarikh_komaki",
            start_date,
            end_date
        )

        # Normalize data types before merge
        data_cpy["ID"] = pd.to_numeric(
            data_cpy["ID"], errors="coerce"
        ).astype("Int64")
        data_cpy["hash"] = data_cpy["hash"].astype(str)

        hash_table = self.hash_table.copy()
        hash_table["ID"] = pd.to_numeric(
            hash_table["ID"], errors="coerce"
        ).astype("Int64")
        hash_table["hash"] = hash_table["hash"].astype(str)

        # Join incoming data with stored hash table
        merged = data_cpy.merge(
            hash_table,
            on="ID",
            how="left",
            suffixes=("", "_db")
        )

        # Existing ID but different hash → update required
        row_update = merged[
            (merged["hash_db"].notna()) &
            (merged["hash"] != merged["hash_db"])
        ]["ID"].tolist()

        # Missing ID in hash table → insert required
        row_create = merged[
            merged["hash_db"].isna()
        ]["ID"].tolist()

        return row_update, row_create


class UpdateHash(ABC):

    @abstractmethod
    def update_hash(
        self,
        data: pd.DataFrame,
        list_id: list,
        update_obj: UpdateData,
        connection
    ) -> None:
        """
        Updates existing hash rows in persistence layer.
        """
        pass


class UpdateHashSell(UpdateHash):
    """
    Concrete update strategy for sales hash records.
    """

    def __init__(self, date_now):
        self.date_now = date_now

    def update_hash(
        self,
        data: pd.DataFrame,
        list_id: list,
        update_obj: UpdateData,
        connection
    ) -> None:

        # Select only rows that require updating
        data_cpy = data[data["ID"].isin(list_id)].copy()

        hash_data = pd.DataFrame({
            "ID": data_cpy["ID"],
            "hash": data_cpy["hash"],
            "DateUpdate": self.date_now
        })

        # Delegate bulk update to infrastructure layer
        update_obj.update_data(
            table="Fact_Hash",
            data=hash_data,
            connection=connection,
            key_column="ID"
        )