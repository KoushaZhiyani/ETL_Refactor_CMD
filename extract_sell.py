import pandas as pd
from abc import ABC, abstractmethod

class BaseExtractor(ABC):

    def __init__(self, repo, log):
        self._repo = repo
        self._log = log

    @abstractmethod
    def extract(self):
        pass

class ExtractSellData(BaseExtractor):


    def extract(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

        self._log.info("Extracting sell data")

        data_vw = self._repo.select_data("AlirezaSales")
        invo_df = self._repo.select_data("InvcnoList")
        recorder_df = self._repo.select_data("Fact_Recorder")

        self._log.info("Extracting Done")

        return data_vw, invo_df, recorder_df


class ExtractCustomerData(BaseExtractor):


    def extract(self) -> tuple[pd.DataFrame, pd.DataFrame]:

        self._log.info("Extracting customer data")

        custom_df = self._repo.select_data("Dim_Custom")
        map_df = self._repo.select_data("Bridge_Vistor_Customer")

        return custom_df, map_df


class ExtractHashData(BaseExtractor):

    def extract(self) -> tuple[pd.DataFrame, pd.DataFrame]:

        data_vw = self._repo.select_data("AlirezaSales")
        hash_df = self._repo.select_data("Fact_Hash")

        return data_vw, hash_df

# recorder_df = conn.read_table_from_sql("Fact_Recorder")
# first_record = recorder_df.loc[0, "Number"]
#
# invc_df = conn.read_table_from_sql("InvcnoList")
# df = conn.read_table_from_sql("AlirezaSales")
#
# logging.info("Preprocessing Starting.")
#
# filtered_df = preprocessing(df)
# sell_flag = 0
#
# logging.info("Sell Starting.")
#
# sell_count_flag, sell_df_temp = check_count_flag(recorder_df, filtered_df, 0)
# unchecked_invc = invc_check(sell_df_temp, [x for x in invc_df['invcno'].tolist()])
