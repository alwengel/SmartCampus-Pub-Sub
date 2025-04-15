import sqlite3

class DBHandler:
    def __init__(self, db_path):
        """
        Initializes the database handler with a path to the SQLite database file.
        """
        self.db_path = db_path
        self.connection = None
        self.cursor = None

    def connect(self):
        """
        Establishes a connection to the SQLite database.
        """
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
            print("Database connection established.")
        except sqlite3.Error as e:
            print(f"An error occurred while connecting to the database: {e}")

    def close(self):
        """
        Closes the database connection.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print("Database connection closed.")


    def __enter__(self):
        """
        Allows the use of 'with' statements for managing the database connection.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Ensures the connection is closed after usage.
        """
        self.close()


    def get_subscriptions(self, version="sql"):
            """
            Retrieves subscriptions in either 'sql' or 'nlp' format.

            Args:
                version (str): Either 'sql' or 'nlp' to choose subscription type.

            Returns:
                List[Dict]: A list of subscriptions with id and the selected version.
            """
            if version not in ("sql", "nlp"):
                raise ValueError("version must be either 'sql' or 'nlp'")

            column_name = "sql_subscription" if version == "sql" else "nlp_subscription"

            try:
                query = f"SELECT id, {column_name} FROM subscriptions"
                self.cursor.execute(query)
                rows = self.cursor.fetchall()

                subscriptions = [
                    {"subscription_id": row[0], "subscription": row[1]} for row in rows
                ]
                return subscriptions

            except sqlite3.Error as e:
                print(f"An error occurred while fetching subscriptions: {e}")
                return []


if __name__=="__main__":

    database = "smartcampus.db"

    with DBHandler(database) as db:
        sql_subs = db.get_subscriptions("sql")
        nlp_subs = db.get_subscriptions("nlp")
        
        print("SQL SUBS:")
        for sub in sql_subs:
            print(sub)

        print()
        print("NLP SUBS:")
        for sub in nlp_subs:
            print(sub)
