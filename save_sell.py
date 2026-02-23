from abc import abstractmethod, ABC

class BaseSave(ABC):

    def __init__(self, repo, log):
        self._repo = repo
        self._log = log

    @abstractmethod
    def save(self):
        pass


class SaveSellData(BaseSave):

    def save(self, data: Dict[str, pd.DataFrame], connection: Connection) -> None:


        self._repo.save_data(table_name="Fact_Sell", data=data["Fact_Sell"], connection=connection)
        self._repo.save_data(table_name="Fact_Recorder", data=data["Fact_Recorder"], connection=connection)


class SaveSellCustomer(BaseSave):

    def save(self, data: Dict[str, pd.DataFrame], connection: Connection) -> None:


        self._repo.save_data(table_name="Dim_Custom", data=data["Dim_Custom"], connection=connection)
        self._repo.save_data(table_name="Bridge_Vistor_Customer", data=data["Bridge_Vistor_Customer"], connection=connection)


