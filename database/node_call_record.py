from scheduler.database.connector import DatabaseConnector as DBC
from scheduler.database.models import DBNodeCallRecordModel


class DBNodeCallRecord:
    __tablename__ = "node_call_records"

    @classmethod
    def get_for_node(cls, db: DBC, node_id: str):
        sql = f"SELECT * FROM {cls.__tablename__} WHERE node_id=%s AND timestamp >= DATE_SUB(NOW(), INTERVAL 8 HOUR)"
        data = (node_id,)
        db.cursor.execute(sql, data)

        return db.cursor.fetchall()

    @classmethod
    def get_statistics(cls, db: DBC) -> list[DBNodeCallRecordModel]:
        sql = """
        SELECT 
            n.id AS id,
            n.name AS name,
            endpoint,
            COUNT(c.id) AS call_count,
            AVG(c.duration) AS average_execution_duration,
            MIN(c.duration) AS minimum_execution_duration,
            MAX(c.duration) AS maximum_execution_duration,
            IFNULL(SUM(CASE WHEN c.outcome = 'success' THEN 1 ELSE 0 END) / COUNT(c.id), 0) AS success_rate
        FROM 
            nodes n
        LEFT JOIN 
            node_call_records c ON n.id = c.node_id
        WHERE
            n.critical = 0 AND n.static = 0 AND c.timestamp >= DATE_SUB(NOW(), INTERVAL 8 HOUR)
        GROUP BY 
            n.id, n.name, c.endpoint;
        """
        db.cursor.execute(sql)

        return db.cursor.fetchall()

    @classmethod
    def insert(cls, db: DBC, node_id: str, endpoint: str, duration: float, outcome: str) -> None:
        sql = f"INSERT INTO {cls.__tablename__}(node_id, endpoint, duration, outcome) VALUES (%s, %s, %s, %s)"
        data = (node_id, endpoint, duration, outcome)
        db.cursor.execute(sql, data)
