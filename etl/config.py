import urllib
import pandas as pd
from sqlalchemy import create_engine, NVARCHAR, text
import re


class SqlConnection:


    def __init__(self, server: object = "localhost", database: object = "PWBCity") -> None:

        self.CONNECTIONS =(f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                                f"SERVER={server};"
                                f"DATABASE={database};"
                                f"Trusted_Connection=yes;")

        self.engine = self.create_engn()

        # self.table_dtype_mapping  = {
        #     "Fact_Sell": {
        #         "invckind": NVARCHAR(80),
        #         "custname": NVARCHAR(200),
        #         "description": NVARCHAR(500)},
        #     "Fact_Return":
        #         {"invckind": NVARCHAR(80),
        #         "custname": NVARCHAR(200),
        #         "description": NVARCHAR(500)},
        #     "Dim_Custom": {
        #     "name": NVARCHAR(200),
        #     "Customer_Group": NVARCHAR(500),
        #     "Geographic_Customer_Group": NVARCHAR(500)
        #         },
        #     "Fact_Sell_total":{
        #         "source": NVARCHAR(20),
        #         "invckind": NVARCHAR(80),
        #         "custname": NVARCHAR(200),
        #         "description": NVARCHAR(500)
        #     },
        #     "Fact_Return_total":
        #         {"source": NVARCHAR(20),
        #          "invckind": NVARCHAR(80),
        #          "custname": NVARCHAR(200),
        #          "description": NVARCHAR(500)
        #          },
        #     "Dim_Dates":
        #         {"jmonthT": NVARCHAR(80),
        #          "jnime": NVARCHAR(80),
        #          "JQuarterT": NVARCHAR(80),
        #          "JWeekDay": NVARCHAR(80)
        #          }
        #     }
        #
        #
        # self.SELF_TABLE = {"Bridge_Vistor_Customer", "Dim_Dates", "Dim_Product", "Dim_Custom",
        #                    "Fact_Recorder", "Fact_Return", "Fact_Sell", "Dim_Visitor", "Fact_Hash"}

    def create_engn(self):

            params = urllib.parse.quote_plus(
                self.CONNECTIONS
            )

            return create_engine("mssql+pyodbc:///?odbc_connect=%s" % params)


    # def read_table_from_sql(self, table_name: str) -> pd.DataFrame:
    #     """
    #     خواندن کامل یک جدول از دیتابیس با استفاده از SQLAlchemy engine
    #     """
    #     # بررسی نام جدول برای امنیت
    #
    #
    #     if (not re.match(r'^[\w_]+$', table_name)) and (table_name not in self.SELF_TABLE):
    #         raise ValueError(f"Invalid table name: {table_name}")
    #
    #     query = f"SELECT * FROM {table_name}"
    #     df = pd.read_sql(query, self.engine)
    #
    #     return df


    # def save_table_to_sql(self, df: pd.DataFrame, table_name: str, if_exists='append', conn=None) -> None:
    #     """
    #     ذخیره دیتافریم در SQL Server
    #     پارامترها:
    #     df: دیتافریم مورد نظر
    #     table_name: نام جدول در دیتابیس
    #     if_exists: رفتار در صورت وجود جدول ('replace'، 'append'  'fail')
    #
    #     """
    #     dtype_mapping = self.table_dtype_mapping.get(table_name, None)
    #     target_conn = conn if conn is not None else self.engine  # 🔹 اگر conn داده شده، از همان استفاده کن
    #
    #     df.to_sql(
    #         name=table_name,
    #         con=target_conn,
    #         schema="dbo",
    #         index=False,
    #         if_exists=if_exists,
    #         dtype=dtype_mapping
    #     )
    #


    def execute_query(self, query: str, params: dict = None, conn=None) -> None:
        """
        اجرای یک کوئری SQL (مثلاً DELETE, UPDATE, INSERT) روی دیتابیس
        """

        if conn is not None:
            conn.execute(text(query), params)

        else:
            with self.engine.begin() as conn:
                if params:
                    conn.execute(text(query), params)
                else:
                    conn.execute(text(query))



