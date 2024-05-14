from scheduler.database.connector import DatabaseConnector as DBC


class DBWorkflowUsageRecord:
    __tablename__ = "workflow_usage_records"

    @classmethod
    def get_statistics(cls, db: DBC):
        sql = """
        SELECT 
            w.id AS id,
            w.name AS name,
            COUNT(u.id) AS usage_count
        FROM 
            workflows w
        LEFT JOIN 
            workflow_usage_records u ON w.id = u.workflow_id
        GROUP BY 
            w.id, w.name;
        """
        db.cursor.execute(sql)

        return db.cursor.fetchall()

    @classmethod
    def insert(cls, db: DBC, workflow_id: int) -> None:
        sql = f"INSERT INTO {cls.__tablename__}(workflow_id) VALUES (%s)"
        data = (workflow_id,)
        db.cursor.execute(sql, data)
