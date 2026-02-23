from abc import ABC, abstractmethod
import pandas as pd
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.types import NVARCHAR
from sqlalchemy import create_engine, text, bindparam
import urllib.parse


class EngineFactory(ABC):
    """
    Abstract factory responsible for creating SQLAlchemy Engine instances.

    This abstraction follows the Dependency Inversion Principle (DIP),
    allowing higher-level modules to depend on an interface rather than
    a concrete database implementation.
    """

    @abstractmethod
    def create(self, server: str, database: str) -> Engine:
        """
        Create and return a configured SQLAlchemy Engine.

        Args:
            server (str): Database server address or name.
            database (str): Target database name.

        Returns:
            Engine: Configured SQLAlchemy Engine instance.
        """
        pass


class SqlServerEngineFactory(EngineFactory):
    """
    Concrete implementation of EngineFactory for Microsoft SQL Server.

    This implementation uses pyodbc as the DBAPI driver and enables
    performance optimizations such as fast_executemany.
    """

    def create(self, server: str, database: str) -> Engine:
        """
        Build a SQLAlchemy Engine for SQL Server using a trusted connection.

        The ODBC connection string is URL-encoded before being passed
        to SQLAlchemy.

        Args:
            server (str): SQL Server hostname or instance.
            database (str): Database name.

        Returns:
            Engine: SQLAlchemy Engine configured for SQL Server.
        """

        # Build raw ODBC connection string
        connection_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
        )

        # Encode connection string to be safely embedded in the URL
        params = urllib.parse.quote_plus(connection_str)

        # Create and return SQLAlchemy engine
        # fast_executemany significantly improves bulk insert performance
        return create_engine(
            f"mssql+pyodbc:///?odbc_connect={params}",
            fast_executemany=True
        )


class SelectData(ABC):
    """
    Abstract base class that defines the contract for data selection
    from a data source.

    Any concrete implementation must implement the `select_data` method.
    """

    @abstractmethod
    def select_data(self, table_name: str) -> pd.DataFrame:
        """
        Retrieve all records from the specified table.

        :param table_name: Name of the table to query.
        :return: DataFrame containing table data.
        """
        pass


class SelectDataSql(SelectData):
    """
    Concrete implementation of SelectData for SQL databases
    using a SQLAlchemy engine.

    This class restricts selectable tables to a predefined whitelist
    in order to prevent unauthorized access or SQL injection.
    """

    def __init__(self, engine):
        """
        Initialize the SQL data selector.

        :param engine: SQLAlchemy Engine instance used to execute queries.
        """
        self.engine = engine

        # Whitelisted tables allowed to be queried.
        # This prevents arbitrary table access and enhances security.
        self.__SELF_TABLE = {
            "Bridge_Vistor_Customer",
            "Dim_Dates",
            "Dim_Product",
            "Dim_Custom",
            "Fact_Recorder",
            "Fact_Return",
            "Fact_Sell",
            "Dim_Visitor",
            "Fact_Hash"
        }


    def select_data(self, table_name: str) -> pd.DataFrame:
        """
        Fetch all records from the given table if it is in the whitelist.

        :param table_name: Name of the table to query.
        :return: DataFrame containing all rows from the table.
        :raises ValueError: If the table name is not allowed.
        """

        # Validate table name against whitelist to prevent SQL injection
        if table_name not in self.__SELF_TABLE:
            raise ValueError("Invalid table name")

        # Construct query (safe because table name is validated)
        query = f"SELECT * FROM {table_name}"

        # Execute query and load results into a pandas DataFrame
        df = pd.read_sql(query, self.engine)

        return df




class SaveData(ABC):
    """
    Abstract base class that defines the contract for persisting
    pandas DataFrames into a data storage system.

    This abstraction allows different storage backends
    (e.g., SQL Server, PostgreSQL, S3, etc.)
    to implement their own save logic.
    """

    @abstractmethod
    def save_data(
        self,
        table_name: str,
        data: pd.DataFrame,
        connection: Connection
    ) -> None:
        """
        Persist the given DataFrame into the specified table.

        Args:
            table_name (str): Target database table name.
            data (pd.DataFrame): DataFrame to be stored.
            connection (Connection): Active SQLAlchemy connection
                                     (typically within a transaction scope).

        Returns:
            None
        """
        pass


class SaveDataSQL(SaveData):
    """
    Concrete implementation of SaveData for SQL-based databases.

    Uses pandas.to_sql under the hood and supports:
        - Schema selection
        - if_exists behavior
        - Custom dtype mapping per table
    """

    def __init__(self, method="append", schema="dbo", index=False):
        """
        Initialize the SQL saver.

        Args:
            method (str): Behavior if table exists ('append', 'replace', 'fail').
            schema (str): Target database schema.
            index (bool): Whether to write the DataFrame index to SQL.
        """
        self.method = method
        self.schema = schema
        self.index = index

        # Table-specific SQL type overrides.
        # This ensures correct NVARCHAR sizing when writing to SQL Server.
        self._table_dtype_mapping = {

            "Fact_Sell": {
                "invckind": NVARCHAR(80),
                "custname": NVARCHAR(200),
                "description": NVARCHAR(500)
            },

            "Fact_Return": {
                "invckind": NVARCHAR(80),
                "custname": NVARCHAR(200),
                "description": NVARCHAR(500)
            },

            "Dim_Custom": {
                "name": NVARCHAR(200),
                "Customer_Group": NVARCHAR(500),
                "Geographic_Customer_Group": NVARCHAR(500)
            },

            "Fact_Sell_total": {
                "source": NVARCHAR(20),
                "invckind": NVARCHAR(80),
                "custname": NVARCHAR(200),
                "description": NVARCHAR(500)
            },

            "Fact_Return_total": {
                "source": NVARCHAR(20),
                "invckind": NVARCHAR(80),
                "custname": NVARCHAR(200),
                "description": NVARCHAR(500)
            },

            "Dim_Dates": {
                "jmonthT": NVARCHAR(80),
                "jnime": NVARCHAR(80),
                "JQuarterT": NVARCHAR(80),
                "JWeekDay": NVARCHAR(80)
            }

        }

    def save_data(
        self,
        table_name: str,
        data: pd.DataFrame,
        connection: Connection
    ) -> None:
        """
        Save DataFrame into the database table using pandas.to_sql.

        Notes:
            - Skips execution if the DataFrame is empty.
            - Applies table-specific dtype mapping when available.
            - Assumes transaction management is handled externally.
        """

        # Avoid unnecessary DB calls if there is no data
        if data.empty:
            return

        # Retrieve optional dtype mapping for the given table
        dtype_mapping = self._table_dtype_mapping.get(table_name)

        # Execute bulk insert using pandas
        data.to_sql(
            name=table_name,
            con=connection,
            schema=self.schema,
            if_exists=self.method,
            index=self.index,
            dtype=dtype_mapping,
            method="multi"
        )


class UpdateData(ABC):
    """
    Abstract base class defining the interface for updating data in a database table.
    """

    @abstractmethod
    def update_data(self, table: str, connection: Connection, data: pd.DataFrame, key_column: str = "ID") -> None:
        """
        Abstract method to update data in a database table.

        Args:
            table (str): The name of the table to update.
            connection (Connection): SQLAlchemy connection object.
            data (pd.DataFrame): DataFrame containing the data to update.
            key_column (str): Name of the primary key column to match rows. Defaults to "ID".
        """
        pass


class UpdateDataSQL(UpdateData):
    """
    Concrete implementation of UpdateData using SQLAlchemy.
    """

    def __init__(self):

        self.__SELF_TABLE = {
            "Dim_Custom",
            "Fact_Recorder",
            "Fact_Return",
            "Fact_Sell",
            "Fact_Hash"
        }

    def update_data(self, table: str, connection: Connection, data: pd.DataFrame, key_column: str = "ID") -> None:
        """
        Update existing rows in the specified table based on the key column.
        Uses bulk execution for efficiency and safety.

        Args:
            table (str): Name of the database table.
            connection (Connection): SQLAlchemy connection object.
            data (pd.DataFrame): DataFrame containing updated values.
            key_column (str): Column used as the primary key for matching rows. Defaults to "ID".
        """


        if table not in self.__SELF_TABLE:
            raise ValueError(f"{table} is not a valid table name")


        # If the DataFrame is empty, nothing to update
        if data.empty:
            return

        # Ensure the key column exists in the DataFrame
        if key_column not in data.columns:
            raise ValueError(f"{key_column} not found in DataFrame columns")

        # Identify columns to update (all except the key column)
        update_cols = [col for col in data.columns if col != key_column]

        if len(update_cols) == 0:

            raise RuntimeError(f"{key_column} is empty")

        # Build the SET clause for the SQL UPDATE statement
        set_clause = ", ".join([f"{col} = :{col}" for col in update_cols])
        query = f"UPDATE {table} SET {set_clause} WHERE {key_column} = :{key_column}"

        # Convert query to SQLAlchemy text object
        stmt = text(query)

        # Convert DataFrame to list of dictionaries for bulk execution
        params_list = data.to_dict(orient="records")

        # Execute the bulk update
        try:
            connection.execute(stmt, params_list)
        except Exception as e:
            # Uncomment the next line if you have a logger configured
            # logger.error(f"Error updating table {table}: {e}")
            raise

class DeleteData(ABC):

    @abstractmethod
    def delete(self, table: str, connection: Connection, data: pd.DataFrame, key_column: str = "ID") -> None:
        pass

class DeleteDataSQL(DeleteData):

    def __init__(self):

        self.__SELF_TABLE = {
            "Dim_Custom",
            "Fact_Recorder",
            "Fact_Return",
            "Fact_Sell",
            "Fact_Hash"
        }

    def delete(self, table: str, connection: Connection, data: pd.DataFrame, key_column: str = "ID") -> None:

        if table not in self.__SELF_TABLE:
            raise ValueError(f"{table} is not a valid table name")

        if data.empty:
            return

        if key_column not in data.columns:
            raise ValueError(f"{key_column} not found in DataFrame columns")

        ids = data[key_column].dropna().unique().tolist()

        if not ids:
            return


        stmt = text(
            f"DELETE FROM {table} WHERE {key_column} IN :ids"
        ).bindparams(bindparam("ids", expanding=True))


        connection.execute(stmt, {"ids": tuple(ids)})