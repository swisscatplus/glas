import json
from datetime import datetime
from typing import Optional

from .connector import DatabaseConnector
from .models import TasksStatisticsEntry, DBTaskModel
from ..orchestrator.models import TaskDifference


class DBTask:
    __tablename__ = "tasks"

    @classmethod
    def get(cls, db: DatabaseConnector, uuid: str) -> Optional[DBTaskModel]:
        sql = f"SELECT * FROM {cls.__tablename__} WHERE id = %s"
        data = (uuid,)
        db.cursor.execute(sql, data)

        entry = db.cursor.fetchone()
        if entry is not None:
            entry["args"] = json.loads(entry["args"]) if entry["args"] else None
            return DBTaskModel(**entry)
        return None

    @classmethod
    def exists(cls, db: DatabaseConnector, uuid: str) -> bool:
        return cls.get(db, uuid) is not None

    @classmethod
    def purge(cls, db: DatabaseConnector) -> None:
        sql = f"DELETE FROM {cls.__tablename__}"
        db.cursor.execute(sql)

    @classmethod
    def insert(cls, db: DatabaseConnector, uuid: str, workflow_id: int, args: Optional[dict[str, any]] = None):
        sql = f"INSERT INTO {cls.__tablename__}(id, workflow_id, task_state_id, args) VALUES(%s, %s, 1, %s)"
        data = (uuid, workflow_id, json.dumps(args) if args is not None else None)
        db.cursor.execute(sql, data)

    @classmethod
    def delete(cls, db: DatabaseConnector, uuid: str) -> None:
        sql = f"DELETE FROM {cls.__tablename__} WHERE id = %s"
        data = (uuid,)
        db.cursor.execute(sql, data)

    @classmethod
    def update_active_step(cls, db: DatabaseConnector, task_id: str, active_step: str) -> None:
        sql = f"UPDATE {cls.__tablename__} SET active_step=%s, updated_at=%s WHERE id=%s"
        data = (active_step, datetime.now(), task_id)
        db.cursor.execute(sql, data)

    @classmethod
    def get_current_week(cls, db: DatabaseConnector) -> list[TasksStatisticsEntry]:
        sql = """
        SELECT t.id AS uuid, w.name AS workflow, ts.name AS state, t.created_at,
            TIMESTAMPDIFF(SECOND, t.created_at, t.updated_at) AS execution_time_seconds
        FROM tasks t
        JOIN workflows w ON t.workflow_id = w.id
        JOIN task_states ts ON t.task_state_id = ts.id
        WHERE ts.name = "FINISHED" AND YEAR(t.created_at) = YEAR(CURRENT_DATE()) AND WEEK(t.created_at) = WEEK(CURRENT_DATE());
        """
        db.cursor.execute(sql)

        return [TasksStatisticsEntry(**entry) for entry in db.cursor.fetchall()]

    @classmethod
    def get_last_week(cls, db: DatabaseConnector) -> list[TasksStatisticsEntry]:
        sql = """
        SELECT t.id AS uuid, w.name AS workflow, ts.name AS state, t.created_at,
            TIMESTAMPDIFF(SECOND, t.created_at, t.updated_at) AS execution_time_seconds
        FROM tasks t
        JOIN workflows w ON t.workflow_id = w.id
        JOIN task_states ts ON t.task_state_id = ts.id
        WHERE ts.name = "FINISHED" AND YEAR(t.created_at) = YEAR(CURRENT_DATE()) AND WEEK(t.created_at) = WEEK(CURRENT_DATE()) - 1;
        """
        db.cursor.execute(sql)

        return [TasksStatisticsEntry(**entry) for entry in db.cursor.fetchall()]

    @classmethod
    def get_last_vs_current_week_percentage(cls, db: DatabaseConnector) -> TaskDifference:
        sql = """
        SELECT
            IFNULL(this_week_task_count, 0) AS this_week_task_count,
            IFNULL(last_week_task_count, 0) AS last_week_task_count,
            CASE
                WHEN last_week_task_count = 0 THEN NULL
                ELSE ((this_week_task_count - last_week_task_count) / last_week_task_count) * 100
            END AS percentage_difference
        FROM
            (SELECT COUNT(*) AS this_week_task_count
            FROM tasks
            JOIN task_states ts ON task_state_id = ts.id
            WHERE ts.name = "FINISHED" AND YEAR(created_at) = YEAR(CURRENT_DATE())
            AND WEEK(created_at) = WEEK(CURRENT_DATE())) AS this_week
        LEFT JOIN
            (SELECT COUNT(*) AS last_week_task_count
            FROM tasks
            JOIN task_states ts ON task_state_id = ts.id
            WHERE ts.name = "FINISHED" AND YEAR(created_at) = YEAR(CURRENT_DATE())
            AND WEEK(created_at) = WEEK(CURRENT_DATE()) - 1) AS last_week ON 1 = 1;
        """
        db.cursor.execute(sql)

        return TaskDifference(**db.cursor.fetchone())

    @classmethod
    def set_active(cls, db: DatabaseConnector, uuid: str) -> None:
        sql = f"UPDATE {cls.__tablename__} SET task_state_id=2, updated_at=%s WHERE id=%s"
        data = (datetime.now(), uuid)
        db.cursor.execute(sql, data)

    @classmethod
    def set_error(cls, db: DatabaseConnector, uuid: str) -> None:
        sql = f"UPDATE {cls.__tablename__} SET task_state_id=4, active_step=NULL, updated_at=%s WHERE id=%s"
        data = (datetime.now(), uuid)
        db.cursor.execute(sql, data)

    @classmethod
    def set_finished(cls, db: DatabaseConnector, uuid: str) -> None:
        sql = f"UPDATE {cls.__tablename__} SET task_state_id=3, active_step=NULL, updated_at=%s WHERE id=%s"
        data = (datetime.now(), uuid)
        db.cursor.execute(sql, data)
