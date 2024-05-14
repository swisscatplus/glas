from task_scheduler.database.connector import DatabaseConnector
from task_scheduler.database.models import DBNodeModel


class DBNode:
    __tablename__ = "nodes"

    @classmethod
    def exists(cls, db: DatabaseConnector, _id: str) -> bool:
        sql = f"SELECT id FROM {cls.__tablename__} WHERE id = %s"
        data = (_id,)
        db.cursor.execute(sql, data)

        return db.cursor.fetchone() is not None

    @classmethod
    def get_by_name(cls, db: DatabaseConnector, name: str) -> DBNodeModel:
        sql = f"SELECT * FROM {cls.__tablename__} WHERE name = %s"
        data = (name,)
        db.cursor.execute(sql, data)
        return DBNodeModel(**db.cursor.fetchone())

    @classmethod
    def insert(
        cls,
        db: DatabaseConnector,
        _id: str,
        name: str,
        static: bool = True,
        critical: bool = False,
        source_node: str | None = None,
        destination_node: str | None = None,
    ):
        if cls.exists(db, _id):
            return

        sql = f"INSERT INTO {cls.__tablename__} VALUES(%s, %s, %s, %s, %s, %s)"
        data = (_id, name, static, critical, source_node, destination_node)
        db.cursor.execute(sql, data)
