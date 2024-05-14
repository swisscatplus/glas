import mysql.connector as connector


class DatabaseConnector:
    __host__ = "127.0.0.1"
    __user__ = "epfl"
    __pwd__ = "Super2019"
    __port__ = 3306
    __dbname__ = "epfl"

    def __init__(self) -> None:
        try:
            self.conn = connector.connect(
                user=self.__user__,
                password=self.__pwd__,
                host=self.__host__,
                database=self.__dbname__,
                port=self.__port__,
            )
        except Exception as e:
            print(e)
            print("Cannot connect to the database")
            exit(1)
        self.conn.autocommit = True
        self.cursor = self.conn.cursor(dictionary=True)

    def is_connected(self) -> bool:
        try:
            self.conn.ping()
        except:
            return False
        return True
