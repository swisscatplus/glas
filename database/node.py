"""
This module contains the class used to interact with the `nodes` table in the database.
"""

from datetime import datetime

from .connector import DatabaseConnector
from .models import DBNodeModel


class DBNode:
    # pylint: disable=missing-class-docstring
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
    def update_state(cls, db: DatabaseConnector, _id: str, state_id: int) -> None:
        sql = f"UPDATE {cls.__tablename__} SET node_state_id = %s, updated_at = %s WHERE id = %s"
        data = (state_id, datetime.now(), _id)
        db.cursor.execute(sql, data)

    @classmethod
    def insert(cls, db: DatabaseConnector, _id: str, name: str):
        if cls.exists(db, _id):
            return

        sql = f"INSERT INTO {cls.__tablename__} VALUES(%s, %s, 1, %s)"
        data = (_id, name, datetime.now())
        db.cursor.execute(sql, data)
