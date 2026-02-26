from abc import abstractmethod, ABC
from typing import Dict
import pandas as pd
from sqlite3 import Connection


class BaseSave(ABC):
    """
    Abstract base class for persistence use cases.

    Each concrete implementation defines how processed
    datasets should be written to the database.
    """

    def __init__(self, repo, log):
        # Repository abstraction responsible for data persistence
        self._repo = repo

        # Logger instance for tracing save operations
        self._log = log

    @abstractmethod
    def save(self, data: Dict[str, pd.DataFrame], connection: Connection):
        """
        Persists one or more DataFrames into the database.

        Args:
            data: Dictionary mapping table names to DataFrames.
            connection: Active database connection.
        """
        pass


class SaveSellData(BaseSave):
    """
    Persists sales-related fact tables.
    """

    def save(self, data: Dict[str, pd.DataFrame], connection: Connection) -> None:

        # Insert processed sales fact data
        self._repo.save_data(
            table_name="Fact_Sell",
            data=data["Fact_Sell"],
            connection=connection
        )

        # Insert recorder tracking data
        self._repo.save_data(
            table_name="Fact_Recorder",
            data=data["Fact_Recorder"],
            connection=connection
        )


class SaveSellCustomer(BaseSave):
    """
    Persists customer dimension and bridge tables.
    """

    def save(self, data: Dict[str, pd.DataFrame], connection: Connection) -> None:

        # Insert customer dimension data
        self._repo.save_data(
            table_name="Dim_Custom",
            data=data["Dim_Custom"],
            connection=connection
        )

        # Insert visitor-customer relationship mapping
        self._repo.save_data(
            table_name="Bridge_Vistor_Customer",
            data=data["Bridge_Vistor_Customer"],
            connection=connection
        )