from task_scheduler.database.connector import DatabaseConnector
from task_scheduler.database.models import DBWorkflowModel


class DBWorkflow:
    __tablename__ = "workflows"

    @classmethod
    def exists(cls, db: DatabaseConnector, name: str) -> bool:
        sql = f"SELECT id FROM {cls.__tablename__} WHERE name LIKE %s"
        data = (name,)
        db.cursor.execute(sql, data)

        return db.cursor.fetchone() is not None

    @classmethod
    def get_all(cls, db: DatabaseConnector):
        sql = f"SELECT * FROM {cls.__tablename__}"
        db.cursor.execute(sql)
        return [DBWorkflowModel(**entry) for entry in db.cursor.fetchall()]

    @classmethod
    def get_by_name(cls, db: DatabaseConnector, name: str) -> DBWorkflowModel:
        sql = f"SELECT * FROM {cls.__tablename__} WHERE name LIKE %s"
        data = (name,)
        db.cursor.execute(sql, data)
        return DBWorkflowModel(**db.cursor.fetchone())

    @classmethod
    def insert(cls, db: DatabaseConnector, name: str, source_node_id: str, destination_node_id: str):
        sql = f"INSERT INTO {cls.__tablename__}(name, source_node_id, destination_node_id) VALUES(%s, %s, %s)"
        data = (name, source_node_id, destination_node_id)
        db.cursor.execute(sql, data)
