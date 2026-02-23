import pandas as pd
from datetime import datetime
from sqlalchemy import text
from abc import ABC, abstractmethod
from save_database import DeleteDataSQL, UpdateDataSQL


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

    def __init__(self, data: pd.DataFrame, date_now: datetime, table_name: str):
        self.database_data = data
        self.date_now = date_now
        self.table_name = table_name

    def remove_extra_rows(self, view_data, remove_obj: DeleteDataSQL, connection):
        # Filter database rows within the given date range
        database_data = filter_data(self.database_data, 'Tarikh_komaki', 14040101, self.date_now)

        database_data_cpy = database_data.copy()
        view_data_cpy = view_data.copy()

        # Ensure IDs are of type Int64 for safe comparison
        database_data_cpy['ID'] = database_data_cpy['ID'].astype("Int64")
        view_data_cpy['ID'] = view_data_cpy['ID'].astype("Int64")

        # Find IDs that exist in the database but not in the view → candidates for deletion
        extra_ids = pd.DataFrame(
            database_data_cpy.loc[~database_data_cpy['ID'].isin(view_data_cpy['ID']), 'ID'].unique(), columns=['ID'])

        # Delete extra rows using the DeleteDataSQL object
        remove_obj.delete(self.table_name, connection, extra_ids, "ID")


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




# class Hash:
#
#     def __init__(self, df: pd.DataFrame):
#
#         self.engine = SqlConnection()
#         self.customer_unit = CustomerUtils(self.engine.read_table_from_sql("Dim_Custom"))
#         self.hash_table = df
#         self.today = datetime.date(datetime.now())
#         self.return_df = pd.DataFrame()
#         self.return_df_risk_row = pd.DataFrame()
#
#     def check_hash(self, df, time: int):
#
#         hash_temp = []
#         df['Tarikh_komaki'] = df['Tarikh_komaki'].astype(float).astype(int)
#
#         if time < 14040401:
#             filter_df = df[(df['Tarikh_komaki'] <= time) & (df['Tarikh_komaki'] > 14040101)].copy()
#         else:
#             filter_df = df[(df['Tarikh_komaki'] <= time) & (df['Tarikh_komaki'] > 14040101)].copy()
#
#         df['Tarikh_komaki'] = df['Tarikh_komaki'].astype(str)
#
#         filter_df['hash'] = (
#                 filter_df['ID'].astype(str) +
#                 filter_df['netvalue'].astype(str).str.replace("-", "", regex=True)
#         )
#
#         risk_row = []
#         return_df_temp = []
#         return_df_risk = []
#         map_df = self.engine.read_table_from_sql("Bridge_Vistor_Customer")
#         for _, row in filter_df.iterrows():
#             hash_match = self.hash_table['hash'].astype(int) == int(float(row['hash']))
#             id_match = self.hash_table['ID'] == int(float(row['ID']))
#
#             if not self.hash_table[id_match].empty:
#                 ### update
#                 if self.hash_table[hash_match & id_match].empty:
#                     row["Date"] = str(row["shamsi_date"])[:7] + "/01"
#                     row_filtered = row[
#                         ['invckind', 'invcno', 'shamsi_date', 'Customer_ID', 'custname', 'itemno', 'description', 'qty',
#                          'fee',
#                          'netvalue', 'Tarikh_komaki', 'Date', 'ID']]
#
#                     risk_row.append(row['ID'])
#                     return_df_risk.append(row_filtered)
#                     self.update_hash(row)
#
#
#             ### create
#             elif self.hash_table[(self.hash_table['ID'] == row['ID'])].empty:
#
#                 hash_temp.append(self.create_hash(row))
#
#                 row["Date"] = str(row["shamsi_date"])[:7] + "/01"
#                 row_filtered = row[
#                     ['invckind', 'invcno', 'shamsi_date', 'Customer_ID', 'custname', 'itemno', 'description', 'qty',
#                      'fee',
#                      'netvalue', 'visitor_id', 'Tarikh_komaki', 'Date', 'ID']]
#                 row_filtered['visitor_id'], _ = self.customer_unit.get_visitor_id(row['Customer_ID'], map_df,
#                                                                                   pd.DataFrame(columns=["Customer_ID",
#                                                                                                         "visitor_id"]))
#
#                 return_df_temp.append(row_filtered)
#
#         if len(return_df_temp) > 0:
#             return_df_temp = pd.DataFrame(return_df_temp,
#                                           columns=['invckind', 'invcno', 'shamsi_date', 'Customer_ID', 'custname',
#                                                    'itemno', 'description', 'qty', 'fee',
#                                                    'netvalue', 'Tarikh_komaki', 'Date', 'ID'])
#
#             self.return_df = return_df_temp.copy()
#             # self.engine.save_table_to_sql(df=return_df_temp, table_name="Fact_Return", if_exists="append")
#
#         if len(risk_row) > 0:
#             write_message(risk_row, flag=3)
#             return_df_risk_df = pd.DataFrame(return_df_risk,
#                                              columns=['invckind', 'invcno', 'shamsi_date', 'Customer_ID', 'custname',
#                                                       'itemno', 'description', 'qty', 'fee',
#                                                       'netvalue', 'Tarikh_komaki', 'Date', 'ID'])
#             self.return_df_risk_row = return_df_risk_df
#
#         hash_temp = pd.DataFrame(hash_temp, columns=['ID', 'hash', 'DateUpdate'])
#         self.hash_table = pd.concat([self.hash_table, hash_temp], ignore_index=True)
#
#     def remove_extral_row_return(self, df: pd.DataFrame, time: int, test_mode: bool = False):
#         #
#         # ret_df = self.engine.read_table_from_sql("Fact_Return")
#         # ret_df['Tarikh_komaki'] = ret_df['Tarikh_komaki'].astype(float).astype(int)
#         #
#         # # فیلتر تاریخ
#         # if time < 14040401:
#         #     filter_df = ret_df[
#         #         (ret_df['Tarikh_komaki'] <= time) &
#         #         (ret_df['Tarikh_komaki'] > 14040101)
#         #         ].copy()
#         # else:
#         #     filter_df = ret_df[
#         #         (ret_df['Tarikh_komaki'] <= time) &
#         #         (ret_df['Tarikh_komaki'] > 14040101)
#         #         ].copy()
#
#         # ID ها رو یکسان کنیم
#         filter_df['ID'] = filter_df['ID'].astype(int)
#         df['ID'] = df['ID'].astype(int)
#
#         # پیدا کردن ID اضافی
#         extra_ids = filter_df.loc[~filter_df['ID'].isin(df['ID']), 'ID'].unique().tolist()
#
#         if extra_ids:
#             # اجرای واقعی → از دیتابیس حذف کن
#             id_list = ",".join(map(str, extra_ids))
#             query = f"DELETE FROM [dbo].[Fact_Return] WHERE [ID] IN ({id_list})"
#             self.engine.execute_query(query)
#
#         return extra_ids

    # def create_hash(self, row):
    #
    #     try:
    #         hash_df = [row['ID'], str(row['ID']) + str(int(row['netvalue'])).replace("-", ""),
    #                    datetime.date(datetime.now())]
    #         return hash_df
    #
    #     except ValueError:
    #         write_message(row, flag=5)

    # def update_hash(self, row):
    #
    #     self.hash_table.loc[self.hash_table['ID'] == int(float(row['ID'])), 'hash'] = str(row['ID']) + str(
    #         int(row['netvalue'])).replace("-", "")
    #     self.hash_table.loc[self.hash_table['ID'] == int(float(row['ID'])), 'DateUpdate'] = datetime.date(
    #         datetime.now())

#
#
#
#
# def check_hash(df, time, hash_table):
#
#     hash_temp = []
#     df['Tarikh_komaki'] = df['Tarikh_komaki'].astype(float).astype(int)
#
#     if time < 14040401:
#         filter_df = df[df['Tarikh_komaki'] < time & df['Tarikh_komaki'] > 14040101].copy()
#     else:
#         filter_df = df[(df['Tarikh_komaki'] < time) & (df['Tarikh_komaki'] > 14040101)].copy()
#
#     df['Tarikh_komaki'] = df['Tarikh_komaki'].astype(str)
#
#     filter_df['hash'] = (
#             filter_df['ID'].astype(str) +
#             filter_df['netvalue'].astype(str).str.replace("-", "", regex=True)
#     )
#
#
#     risk_row = []
#     return_df_temp_list = []
#     return_df_risk = []
#
#     map_df = conn.read_table_from_sql("Bridge_Vistor_Customer")
#
#     for _, row in filter_df.iterrows():
#         hash_match = hash_table['hash'].astype(int) == int(float(row['hash']))
#         id_match = hash_table['ID'] == int(float(row['ID']))
#
#         if not hash_table[(hash_table['ID'] == int(float(row['ID'])))].empty:
#             ### update
#             if hash_table[int(float(row['hash'])) == hash_table['hash'].astype(int)].empty:
#                 row["Date"] = str(row["shamsi_date"])[:7] + "/01"
#                 row_filtered = row[
#                     ['invckind', 'invcno', 'shamsi_date', 'Customer_ID', 'custname', 'itemno', 'description', 'qty',
#                      'fee',
#                      'netvalue', 'Tarikh_komaki', 'Date', 'ID']]
#
#                 risk_row.append(row['ID'])
#                 return_df_risk.append(row_filtered)
#                 update_hash(row)
#
#
#         ### create
#         elif hash_table[(hash_table['ID'] == row['ID'])].empty:
#
#             hash_temp.append(create_hash(row))
#
#
#             row["Date"] = str(row["shamsi_date"])[:7] + "/01"
#             row_filtered = row[
#                 ['invckind', 'invcno', 'shamsi_date', 'Customer_ID', 'custname', 'itemno', 'description', 'qty', 'fee',
#                  'netvalue', 'visitor_id', 'Tarikh_komaki', 'Date', 'ID']]
#             row_filtered['visitor_id'], _ = get_visitor_id(row['Customer_ID'], map_df, pd.DataFrame(columns=["Customer_ID", "visitor_id"]))
#
#
#             return_df_temp_list.append(row_filtered)
#
#
#     if len(return_df_temp_list) > 0:
#
#         return_df_temp = pd.DataFrame(return_df_temp_list, columns=['invckind', 'invcno', 'shamsi_date', 'Customer_ID', 'custname', 'itemno', 'description', 'qty', 'fee',
#                  'netvalue', 'visitor_id', 'Tarikh_komaki', 'Date', 'ID'])
#
#
#         custom_df = conn.read_table_from_sql("Dim_Custom")
#         new_customers = check_customer_id(return_df_temp['Customer_ID'].unique(), custom_df)
#         if new_customers:
#             custom_df_temp = add_customer(return_df_temp, new_customers)
#
#             # save_table_to_sql(custom_df_temp, "Dim_Custom", "append")
#             write_message(custom_df_temp["Customer_ID"].tolist(), flag=4)
#
#
#         # save_table_to_sql(df=return_df_temp, table_name="Fact_Return", if_exists="append")
#
#
#
#     if len(risk_row) > 0:
#         write_message(risk_row, flag=3)
#         return_df_risk_df = pd.DataFrame(return_df_temp_list,
#                      columns=['invckind', 'invcno', 'shamsi_date', 'Customer_ID', 'custname', 'itemno', 'description',
#                               'qty', 'fee', 'netvalue', 'visitor_id', 'Tarikh_komaki', 'Date', 'ID'])
#         self.return_df_risk_row = return_df_risk_df
#
#     return_df_temp = pd.DataFrame(return_df_temp_list)
#     hash_temp = pd.DataFrame(hash_temp, columns=['ID', 'hash', 'DateUpdate'])
#     hash_table = pd.concat([hash_table, hash_temp], ignore_index=True)
#     # print("custom table: ", custom_df_temp)
#
#
#     save_tables(ret_df=locals().get("return_df_temp", pd.DataFrame()), cus_df=locals().get("custom_df_temp", pd.DataFrame()),
#                 hash_df=locals().get("hash_table", pd.DataFrame()))
#     return hash_table
#
#
#
# def remove_extral_row_return(self, df: pd.DataFrame, time: int, test_mode: bool = False):
#         ret_df = self.engine.read_table_from_sql("Fact_Return")
#
#         # فیلتر تاریخ
#         if time < 14040401:
#             filter_df = ret_df[
#                 (ret_df['Tarikh_komaki'] < time) &
#                 (ret_df['Tarikh_komaki'] > 14040101)
#                 ].copy()
#         else:
#             filter_df = ret_df[
#                 (ret_df['Tarikh_komaki'] < time) &
#                 (ret_df['Tarikh_komaki'] > 14040101)
#                 ].copy()
#
#         # ID ها رو یکسان کنیم
#         filter_df['ID'] = filter_df['ID'].astype(int)
#         df['ID'] = df['ID'].astype(int)
#
#         # پیدا کردن ID اضافی
#         extra_ids = filter_df.loc[~filter_df['ID'].isin(df['ID']), 'ID'].unique().tolist()
#
#         if extra_ids:
#
#             # اجرای واقعی → از دیتابیس حذف کن
#             id_list = ",".join(map(str, extra_ids))
#             query = f"DELETE FROM [dbo].[Fact_Return] WHERE [ID] IN ({id_list})"
#             self.engine.execute_query(text(query))
#
#         return extra_ids
#
#
# def create_hash(self, row):
#     try:
#         hash_df = [row['ID'], str(row['ID']) + str(int(row['netvalue'])).replace("-", ""),
#                    datetime.date(datetime.now())]
#         return hash_df
#
#     except ValueError:
#         write_message(row, flag=5)
#
#
# def update_hash(self, row):
#
#     self.hash_table.loc[self.hash_table['ID'] == int(float(row['ID'])), 'hash'] = str(row['ID']) + str(
#         int(row['netvalue'])).replace("-", "")
#     self.hash_table.loc[self.hash_table['ID'] == int(float(row['ID'])), 'DateUpdate'] = datetime.date(datetime.now())
#
#
# conn = SqlConnection()