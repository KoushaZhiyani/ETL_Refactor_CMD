from sqlite3 import Connection
import pandas as pd
from abc import ABC, abstractmethod


class BaseTransformer(ABC):
    """
    Abstract base class for all data transformers.

    Responsibility:
    - Defines a common interface for transforming DataFrames.
    - Enforces implementation of `transform` method.

    Design:
    - Uses Dependency Injection for pipeline_engine and logger.
    - Follows Open/Closed Principle: new transformers can be added without modifying existing code.
    """

    def __init__(self, pipeline_engine, log):
        # Engine responsible for executing transformation steps
        self._pipeline_engine = pipeline_engine

        # Logger for tracking transformation events/errors
        self._log = log

    @abstractmethod
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Transform input DataFrame and return transformed DataFrame.
        Must be implemented by subclasses.
        """
        pass


class TransformSellData(BaseTransformer):
    """
    Concrete transformer for Sell data.

    Responsibility:
    - Applies sell-specific transformation pipeline.
    """

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        # Work on a copy to avoid mutating original DataFrame (defensive programming)
        data_cpy = data.copy()

        # Delegates transformation logic to pipeline engine
        data_cpy = self._pipeline_engine.run_pipeline(data_cpy)

        return data_cpy


class TransformCustomerData(BaseTransformer):
    """
    Concrete transformer for Customer data.

    Responsibility:
    - Applies customer-specific transformation pipeline.
    """

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        # Avoid side effects by copying input
        data_cpy = data.copy()

        # Execute transformation steps via pipeline engine
        data_cpy = self._pipeline_engine.run_pipeline(data_cpy)

        return data_cpy


class HashRepository(ABC):
    """
    Repository abstraction for hash persistence layer.

    Responsibility:
    - Defines contract for saving, updating and cleaning hash data.
    - Decouples business logic from database implementation.

    Follows:
    - Dependency Inversion Principle
    """

    @abstractmethod
    def save(self, data: pd.DataFrame) -> None:
        pass

    @abstractmethod
    def update(self, data: pd.DataFrame, ids: list[int]) -> None:
        pass

    @abstractmethod
    def remove_extra(self, view_data: pd.DataFrame) -> None:
        pass


class SqlHashRepository(HashRepository):
    """
    SQL-based implementation of HashRepository.

    Responsibility:
    - Coordinates database operations related to hash persistence.

    Design:
    - Uses composition instead of inheritance for DB operations.
    - Injects save/update/remove strategies.
    - Avoids direct SQL logic inside business layer.
    """

    def __init__(self, save_obj, update_obj, remove_obj, connection: Connection):
        # Strategy object responsible for insert operations
        self._save_obj = save_obj

        # Strategy object responsible for update operations
        self._update_obj = update_obj

        # Strategy object responsible for cleaning obsolete rows
        self._remove_obj = remove_obj

        # Database connection injected (not created internally)
        self._connection = connection

    def save(self, data: pd.DataFrame) -> None:
        """
        Persist new hash rows into database.
        """
        self._save_obj.save_data(
            data=data,
            table_name="Fact_Hash",  # Potential improvement: inject instead of hard-code
            conn=self._connection
        )

    def update(self, data: pd.DataFrame, ids: list[int]) -> None:
        """
        Update existing hash rows by their IDs.
        """
        self._update_obj.update_hash(
            data=data,
            list_id=ids,
            update_obj=self._update_obj,
            connection=self._connection
        )

    def remove_extra(self, view_data: pd.DataFrame) -> None:
        """
        Remove rows that no longer exist in source view.
        """
        self._remove_obj.remove_extra_rows(
            view_data=view_data,
            remove_obj=self._remove_obj,
            connection=self._connection
        )


class HashSyncService:
    """
    Application service responsible for synchronizing hash table.

    Responsibility:
    - Orchestrates the hash synchronization process.
    - Coordinates checker, creator, and repository.

    Architecture:
    - Pure orchestration layer (no SQL, no hashing logic).
    - Follows Single Responsibility Principle.
    - All dependencies injected (DIP compliant).
    """

    def __init__(
            self,
            hash_checker,
            hash_creator,
            hash_repository,
            log
    ):
        # Determines which rows need update/create
        self._hash_checker = hash_checker

        # Responsible for generating hash values
        self._hash_creator = hash_creator

        # Abstract repository (can be SQL, NoSQL, API-based, etc.)
        self._repository = hash_repository

        # Logger instance
        self._log = log

    def sync(self, vw_data: pd.DataFrame, date_now):
        """
        Synchronize hash table with view data.

        Flow:
        1. Detect rows to update and create.
        2. Create hashes for new rows.
        3. Persist new hashes.
        4. Update changed hashes.
        5. Remove obsolete rows.
        """

        # Determine required changes
        rows_to_update, rows_to_create = \
            self._hash_checker.check(vw_data, date_now)

        # Insert new rows
        if rows_to_create:
            created_hash = self._hash_creator.create_hash(rows_to_create)
            self._repository.save(created_hash)

        # Update existing rows
        if rows_to_update:
            self._repository.update(vw_data, rows_to_update)

        # Remove outdated rows
        self._repository.remove_extra(vw_data)