from scheduler.database.connector import DatabaseConnector as DBC


class DBNodeProperty:
    __tablename__ = "node_properties"

    @classmethod
    def exists(cls, db: DBC, node_id: str, name: str, value: str) -> bool:
        sql = f"SELECT id FROM {cls.__tablename__} WHERE node_id=%s AND name=%s AND value=%s"
        data = (node_id, name, value)
        db.cursor.execute(sql, data)

        return db.cursor.fetchone() is not None

    @classmethod
    def insert_property(cls, db: DBC, node_id: str, name: str, value: str):
        if cls.exists(db, node_id, name, value):
            return
        
        sql = f"INSERT INTO {cls.__tablename__}(node_id, name, value) VALUES (%s, %s, %s)"
        data = (node_id, name, value)
        db.cursor.execute(sql, data)
