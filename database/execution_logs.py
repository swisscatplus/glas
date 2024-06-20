from glas.database import DatabaseConnector


class DBExecutionLogs:
    __tablename__ = "execution_logs"

    @classmethod
    def insert(cls, db: DatabaseConnector, task_id: str, workflow_id: int, name: str, start: float, end: float):
        sql = f"INSERT INTO {cls.__tablename__}(task_id, workflow_id, name, start, end) VALUES(%s, %s, %s, %s, %s)"
        data = (task_id, workflow_id, name, start, end)
        db.cursor.execute(sql, data)
