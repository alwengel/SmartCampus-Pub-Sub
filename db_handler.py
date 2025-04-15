import sqlite3
import random
import json

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
            self.connection.row_factory = sqlite3.Row
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
                {"subscription_id": row["id"], "subscription": row[column_name]} for row in rows
            ]
            return subscriptions

        except sqlite3.Error as e:
            print(f"An error occurred while fetching subscriptions: {e}")
            return []

    def get_random_publications_with_matches(self, limit, subscription_version="sql"):
        """
        Retrieves a number of random publications with their matching subscriptions.
        :param limit: Number of random publications to fetch.
        :param subscription_version: Either 'sql' or 'nlp' to determine which subscription type to use.
        :return: List of dictionaries with publication and matched subscriptions.
        """
        try:
            self.cursor.execute("SELECT * FROM publications ORDER BY RANDOM() LIMIT ?", (limit,))
            publications = self.cursor.fetchall()

            result = []
            for pub in publications:
                publication_id = pub["id"]
                publication_str = pub["publication"]

                raw_matches = pub["subscription_matches"]
                match_ids = []
                if raw_matches:
                    try:
                        if isinstance(raw_matches, bytes):
                            raw_matches = raw_matches.decode("utf-8")
                        match_ids = json.loads(raw_matches)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        match_ids = []

                matches = []
                for sub_id in match_ids:
                    sub_col = "sql_subscription" if subscription_version == "sql" else "nlp_subscription"
                    self.cursor.execute(f"SELECT {sub_col} AS subscription, id FROM subscriptions WHERE id = ?", (sub_id,))
                    row = self.cursor.fetchone()
                    if row:
                        matches.append({
                            "subscription": row["subscription"],
                            "subscription_id": row["id"]
                        })

                result.append({
                    "publication_id": publication_id,
                    "publication": publication_str,
                    "subscription_matches": matches
                })

            return result
        except sqlite3.Error as e:
            print(f"An error occurred while fetching publications: {e}")
            return []


if __name__=="__main__":
    database = "smartcampus.db"

    with DBHandler(database) as db:
        sql_subs = db.get_subscriptions("sql")
        nlp_subs = db.get_subscriptions("nlp")
        rand_pubs = db.get_random_publications_with_matches(3, "sql")

        print("SQL SUBS:")
        for sub in sql_subs:
            print(sub)

        print("\nNLP SUBS:")
        for sub in nlp_subs:
            print(sub)

        print("\nRandom Publications with Matches:")
        for pub in rand_pubs:
            print(json.dumps(pub, indent=2))
