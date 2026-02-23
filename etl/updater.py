from abc import ABC, abstractmethod
import pandas as pd


# etl/updater.py


class CheckUpdateFlag:
    """
    Utility class responsible for checking whether
    a specific value in a DataFrame matches
    a given record value.

    This class is typically used to determine
    whether an update operation is required.
    """

    def __init__(self, index: int):
        """
        Initialize the checker with a specific row index.

        Parameters
        ----------
        index : int
            The row index in the DataFrame that will be used
            to compare values against the provided record.
        """
        self.index = index

    def check_update(
        self,
        record: int,
        data: pd.DataFrame,
        col: str = "Number"
    ) -> bool:
        """
        Compare the provided record value with
        a specific cell value in the DataFrame.

        Parameters
        ----------
        record : int
            The reference value to compare against.

        data : pd.DataFrame
            The DataFrame containing the data to check.

        col : str, default="Number"
            The column name from which the value
            will be retrieved.

        Returns
        -------
        bool
            True if the record matches the value
            in the specified DataFrame cell,
            otherwise False.
        """
        return record == data.loc[self.index, col]