"""
This module contains the class used to interact with the `steps` table in the database.
"""

from .connector import DatabaseConnector


class DBStep:
    # pylint: disable=missing-class-docstring
    __tablename__ = "steps"

    @classmethod
    def exists(cls, db: DatabaseConnector, workflow_id: int, node_id: str, position: int) -> bool:
        sql = f"SELECT id FROM {cls.__tablename__} WHERE workflow_id=%s AND node_id=%s AND position=%s"
        data = (workflow_id, node_id, position)
        db.cursor.execute(sql, data)
        return db.cursor.fetchone() is not None

    @classmethod
    def get_all_for_workflow(cls, db: DatabaseConnector, workflow_id: int):
        sql = f"SELECT steps.position, n.name FROM {cls.__tablename__} JOIN nodes n ON n.id = steps.node_id WHERE steps.workflow_id=%s"
        data = (workflow_id,)
        db.cursor.execute(sql, data)
        return db.cursor.fetchall()

    @classmethod
    def insert(cls, db: DatabaseConnector, workflow_id: int, node_id: str, position: int) -> None:
        if cls.exists(db, workflow_id, node_id, position):
            return

        sql = f"INSERT INTO {cls.__tablename__}(node_id, workflow_id, position) VALUES (%s, %s, %s)"
        data = (node_id, workflow_id, position)
        db.cursor.execute(sql, data)
