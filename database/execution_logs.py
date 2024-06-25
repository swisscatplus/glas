import datetime

from glas.database import DatabaseConnector
from glas.database.models import DBExecutionLogsModel


class DBExecutionLogs:
    __tablename__ = "execution_logs"

    @classmethod
    def insert(cls, db: DatabaseConnector, task_id: str, workflow_id: int, name: str, start: float, end: float):
        start_dt = datetime.datetime.fromtimestamp(start)
        end_dt = datetime.datetime.fromtimestamp(end)
        sql = f"INSERT INTO {cls.__tablename__}(task_id, workflow_id, name, start, end) VALUES(%s, %s, %s, %s, %s)"
        data = (task_id, workflow_id, name, start_dt, end_dt)
        db.cursor.execute(sql, data)

    @classmethod
    def get(cls, db: DatabaseConnector):
        sql = f"SELECT * FROM {cls.__tablename__} WHERE start >= DATE_SUB(NOW(), INTERVAL 8 HOUR)"
        db.cursor.execute(sql)

        return [DBExecutionLogsModel(**entry) for entry in db.cursor.fetchall()]