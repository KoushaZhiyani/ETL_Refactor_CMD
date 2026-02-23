from sqlite3 import Connection

import pandas as pd
from abc import ABC, abstractmethod


class BaseTransformer(ABC):

    def __init__(self, pipeline_engine, log):

        self._pipeline_engine = pipeline_engine
        self._log = log


    @abstractmethod
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        pass



class TransformSellData(BaseTransformer):

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        # do_list = [DropColumns(), SetValue(), RenameSellColumns(), MapVisitorCustomer(map_df)]
        data_cpy = data.copy()

        data_cpy = self._pipeline_engine.run_pipeline(data_cpy)
        return data_cpy


class TransformCustomerData(BaseTransformer):

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        # do_list = [ExtractCustomerDf(list_customer_unchecked), SetValueCustomers(), MapVisitorCustomer(map_df)]
        data_cpy = data.copy()

        data_cpy = self._pipeline_engine.run_pipeline(data_cpy)
        return data_cpy




class HashRepository(ABC):

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

    def __init__(self, save_obj, update_obj, remove_obj, connection):
        self._save_obj = save_obj
        self._update_obj = update_obj
        self._remove_obj = remove_obj
        self._connection = connection

    def save(self, data: pd.DataFrame) -> None:
        self._save_obj.save_data(
            data=data,
            table_name="Fact_Hash",
            conn=self._connection
        )

    def update(self, data: pd.DataFrame, ids: list[int]) -> None:
        self._update_obj.update_hash(
            data=data,
            list_id=ids,
            update_obj=self._update_obj,
            connection=self._connection
        )

    def remove_extra(self, view_data: pd.DataFrame) -> None:
        self._remove_obj.remove_extra_rows(
            view_data=view_data,
            remove_obj=self._remove_obj,
            connection=self._connection
        )


class HashSyncService:

    def __init__(
            self,
            hash_checker,
            hash_creator,
            hash_repository,
            log
    ):
        self._hash_checker = hash_checker
        self._hash_creator = hash_creator
        self._repository = hash_repository
        self._log = log

    def sync(self, vw_data: pd.DataFrame, date_now):

        rows_to_update, rows_to_create = \
            self._hash_checker.check(vw_data, date_now)

        if rows_to_create:
            created_hash = self._hash_creator.create_hash(rows_to_create)
            self._repository.save(created_hash)

        if rows_to_update:
            self._repository.update(vw_data, rows_to_update)

        self._repository.remove_extra(vw_data)

        # row_update, row_create = CheckHashSell(hash_df).check(vw_data, datetime.datetime.now())
        # row_hash_created =  CreateHashSell(datetime.datetime.now()).create_hash(row_create)
        # UpdateHashSell(datetime.datetime.now()).update_hash(data=vw_data, list_id=row_update, update_obj=update_obj, connection=connection)
        #
        # RemoveExtraRows(data=hash_df, date_now=datetime.datetime.now(),
        #                 "Fact_Return").remove_extra_rows(view_data=vw_data, remove_obj=remove_obj, connection=connection)



