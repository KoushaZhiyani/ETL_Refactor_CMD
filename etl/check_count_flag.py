from abc import ABC, abstractmethod
import pandas as pd


class CheckFlag(ABC):
    """
    Abstract base class that defines the interface
    for flag calculation strategies.

    Each concrete implementation must implement
    the `check_flag` method.
    """

    @abstractmethod
    def check_flag(
        self,
        record: pd.DataFrame,
        data: pd.DataFrame
    ) -> tuple[int, pd.DataFrame]:
        """
        Calculate a flag value based on the given record and dataset.

        Parameters:
        ----------
        record : pd.DataFrame
            DataFrame containing reference values (e.g., previously stored counts).

        data : pd.DataFrame
            The current dataset to compare against.

        Returns:
        -------
        tuple[int, pd.DataFrame]
            - Calculated flag value (difference between current row count and reference value)
            - The original dataset (unchanged)
        """
        pass


class ReturnFlag(CheckFlag):
    """
    Concrete implementation of CheckFlag.

    Computes the flag value using a specific row index
    from the record DataFrame.
    """

    def __init__(self, index: int):
        """
        Initialize the strategy with the row index
        that contains the reference 'Number' value.

        Parameters:
        ----------
        index : int
            Row index in the record DataFrame used
            to extract the reference number.
        """
        self.index = index

    def check_flag(
        self,
        record: pd.DataFrame,
        data: pd.DataFrame
    ) -> tuple[int, pd.DataFrame]:
        """
        Calculate the difference between the current
        dataset row count and the reference number
        located at the specified index.

        Returns:
        -------
        tuple[int, pd.DataFrame]
            - Difference between data row count and reference number
            - The original dataset
        """
        reference_number = record.loc[self.index, "Number"]
        flag_value = data.shape[0] - reference_number

        return flag_value, data
