import pandas as pd
from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    """
    Abstract base class for data extraction use cases.

    Each concrete extractor is responsible for retrieving
    a specific set of datasets from the persistence layer.
    """

    def __init__(self, repo, log):
        # Repository abstraction used for data access
        self._repo = repo

        # Logger instance for tracing extraction flow
        self._log = log

    @abstractmethod
    def extract(self):
        """
        Executes the extraction process.

        Returns:
            One or more pandas DataFrames depending on the use case.
        """
        pass


class ExtractSellData(BaseExtractor):
    """
    Extracts all datasets required for the sales processing pipeline.
    """

    def extract(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

        self._log.info("Extracting sell data")

        # Main sales view
        data_vw = self._repo.select_data("AlirezaSales")

        # Invoice reference data
        invo_df = self._repo.select_data("InvcnoList")

        # Recorder tracking table
        recorder_df = self._repo.select_data("Fact_Recorder")

        self._log.info("Sell data extraction completed")

        return data_vw, invo_df, recorder_df


class ExtractCustomerData(BaseExtractor):
    """
    Extracts datasets required for customer-related processing.
    """

    def extract(self) -> tuple[pd.DataFrame, pd.DataFrame]:

        self._log.info("Extracting customer data")

        # Customer dimension table
        custom_df = self._repo.select_data("Dim_Custom")

        # Mapping between visitor and customer
        map_df = self._repo.select_data("Bridge_Vistor_Customer")

        self._log.info("Customer data extraction completed")

        return custom_df, map_df


class ExtractHashData(BaseExtractor):
    """
    Extracts datasets required for hash synchronization.
    """

    def extract(self) -> tuple[pd.DataFrame, pd.DataFrame]:

        self._log.info("Extracting hash-related data")

        # Source view used for hash comparison
        data_vw = self._repo.select_data("AlirezaSales")

        # Existing hash table from database
        hash_df = self._repo.select_data("Fact_Hash")

        self._log.info("Hash data extraction completed")

        return data_vw, hash_df