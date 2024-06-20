import datetime

from glas.database import DatabaseConnector


class DBLogs:
    __tablename__ = "logs"

    @classmethod
    def db_sink(cls, message):
        record = message.record
        db = DatabaseConnector()

        if db.cursor is not None:
            cls.insert(db, record["time"], record["extra"]["app"], record["level"].name,
                       record["name"], record["function"], record["line"], record["message"])

    @classmethod
    def insert(cls, db: DatabaseConnector, timestamp: datetime.datetime, logger_name: str, log_level: str, module: str,
               function: str, line: int,
               message: str):
        sql = f"INSERT INTO {cls.__tablename__}(timestamp, logger_name, log_level, module, caller, line, message) VALUES(%s, %s, %s, %s, %s, %s, %s)"
        data = (timestamp, logger_name, log_level, module, function, line, message)
        db.cursor.execute(sql, data)
