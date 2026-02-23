from abc import ABC, abstractmethod
import pandas as pd

# -------------------------
# Base Transformer Class
# -------------------------
class Transformer(ABC):
    """
    Abstract base class for all transformers.
    Each transformer must implement the `transform` method
    which takes a DataFrame as input and returns a transformed DataFrame.
    """
    @abstractmethod
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        pass


# -------------------------
# Drop Unnecessary Columns
# -------------------------
class DropColumns(Transformer):
    """
    Transformer to remove specific columns from a DataFrame.
    Useful for cleaning raw data before further processing.
    """
    def transform(self, data):
        # Drop columns: 'مبلغ', 'کاهنده', 'عنوان گروه مشتری'
        return data.drop(
            columns=['مبلغ', 'کاهنده', 'عنوان گروه مشتری']
        )


# -------------------------
# Set Additional Values
# -------------------------
class SetValue(Transformer):
    """
    Transformer to set new columns or modify existing ones.
    Adds a default tag code and formats date strings.
    """
    def transform(self, data):
        data = data.copy()
        # Add a default tag column with value 0
        data['کد تگ 1'] = 0
        # Convert Shamsi date from 'YYYY/MM/DD' to 'YYYYMMDD'
        data['Tarikh_komaki'] = data['shamsi_date'].str.replace("/", "", regex=False)
        data.loc[:, "Date"] = data["shamsi_date"].str[:7] + "/01"

        return data


# -------------------------
# Rename Columns
# -------------------------
class RenameSellColumns(Transformer):
    """
    Transformer to rename columns based on a predefined mapping.
    The COLUMN_MAPPING dict should be defined with old_name: new_name pairs.
    """
    COLUMN_MAPPING = {
        # Example:
        # 'old_column': 'new_column'
    }

    def transform(self, data):
        return data.rename(columns=self.COLUMN_MAPPING)



# -------------------------
# Extract New Customers
# -------------------------
class ExtractCustomerDf(Transformer):
    """
    Transformer to extract customer records that are not yet in the system.
    Filters based on a list of unchecked customer IDs.
    """
    def __init__(self, list_customer_unchecked):
        self.list_customer_unchecked = list_customer_unchecked

    def transform(self, data) -> pd.DataFrame:
        # Identify new customers that are not in the current DataFrame
        new_list_customer = [i for i in self.list_customer_unchecked if i not in set(data['Customer_ID'])]

        # Initialize empty DataFrame with required columns
        custom_df_temp = pd.DataFrame(columns=['name', 'Customer_ID', 'Geographic_Customer_Group', 'Customer_Group'])

        # Fill 'Customer_ID' and 'name' for new customers
        custom_df_temp[['Customer_ID', 'name']] = data[data['Customer_ID'].isin(
            new_list_customer
        )][
            ['Customer_ID', 'custname']]

        # Remove duplicate rows and reset index
        custom_df_temp.drop_duplicates(inplace=True)
        custom_df_temp.reset_index(drop=True, inplace=True)

        return custom_df_temp


# -------------------------
# Set Default Customer Values
# -------------------------
class SetValueCustomers(Transformer):
    """
    Transformer to assign default values to customer-related columns.
    For example, setting default geographic group and customer group.
    """
    def transform(self, data):
        data_cpy = data.copy()
        data_cpy['Customer_Group'] = 'مشهد'
        data_cpy['Geographic_Customer_Group'] = '0'
        return data_cpy


# -------------------------
# Map Visitor ID to Customers
# -------------------------
class MapVisitorCustomer(Transformer):
    """
    Transformer to map each Customer_ID to a visitor_id based on a lookup DataFrame.
    Missing visitor_ids are filled with 0.
    """
    def __init__(self, map_df):
        self.map_df = map_df

    def transform(self, data):
        data = data.copy()

        # Create a mapping from Customer_ID to visitor_id
        mapping = self.map_df.set_index('Customer_ID')['visitor_id']

        # Apply mapping to the DataFrame, fill missing visitor_id with 0
        data['visitor_id'] = data['Customer_ID'].map(mapping).fillna(0)

        return data



# -------------------------
# Pipeline for Data
# -------------------------
class TransformPipeline:
    """
    A pipeline to apply multiple transformers sequentially on data.
    Each transformer is applied in the order they are provided.
    """
    def __init__(self, steps):
        self.steps = steps

    def run_pipeline(self, data):
        """
        Execute all transformers in the pipeline on the input DataFrame.
        Returns the fully transformed DataFrame.
        """
        for step in self.steps:
            data = step.transform(data)
        return data
