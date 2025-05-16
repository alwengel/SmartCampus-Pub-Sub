import sqlite3
import json
import random
import string

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

    def get_semi_structured_publications(self, limit, subscription_version="sql"):
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
                    match_ids = self.decode_blob_to_identifiers(raw_matches)

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
            print(f"An error occurred while fetching SEMI-structured publications: {e}")
            return []
        
    def get_publications_json(self, limit):
        """
        Retrieves a number of random publications with their matching subscription IDs in JSON format.
        :param limit: Number of random publications to fetch.
        :return: List of publications in JSON format with matched subscription IDs.
        """
        try:
            self.cursor.execute("SELECT * FROM publications ORDER BY RANDOM() LIMIT ?", (limit,))
            publications = self.cursor.fetchall()

            result = []
            for pub in publications:
                publication_id = pub["id"]
                raw_matches = pub["subscription_matches"]

                publication_json = {}
                for key in pub.keys():
                    if key not in ("id", "subscription_matches") and pub[key] is not None:
                        publication_json[key] = pub[key]

                publication_json_str = json.dumps(publication_json)

                match_ids = []
                if raw_matches:
                    match_ids = self.decode_blob_to_identifiers(raw_matches)

                result.append({
                    "publication_id": publication_id,
                    "publication": publication_json_str,
                    "subscription_matches": match_ids 
                })

            return result

        except sqlite3.Error as e:
            print(f"An error occurred while fetching JSON publications: {e}")
            return []
   
    def get_publications_with_subscription_matches(self, limit, publication_version="semi", subscription_version="sql"):
        """
        Gets publications with all matching subscriptions in different publication versions.
        :param limit: Number of publications to fetch.
        :param publication_version: Type of publication representation.
        :param subscription_version: Type of subscription representation.
        :return: List of publications with matched subscriptions.
        """
        if publication_version == "semi":
            return self.get_semi_structured_publications(limit, subscription_version)
        elif publication_version == "json":
            return self.get_publications_json(limit)
        else:
            raise ValueError(f"Publication version not supported: {publication_version}")
    
    def inject_noise(self, data, noise_rate=0.1):
        """
        Injects random noise to the subscription data.
        :param data: Subscription data (string).
        :param noise_rate: Number of random characters injected into the data (0.1 == 10%).
        :return: Set of altered subscriptions.
        """
        num_noise = int(len(data) * noise_rate)
        indices = random.sample(range(len(data)), num_noise)
        noisy_data = list(data)
        
        for index in indices:
            random_char = random.choice(string.ascii_letters + string.digits + string.punctuation)
            noisy_data[index] = random_char
        
        return ''.join(noisy_data)
    
    def get_subscriptions_with_errors(self, subscription_version="sql", error_rate=0.1):
        """
        Fetches subscriptions and injects errors based on the error rate.
        :param subscription_version: The type of subscription.
        :param error_rate: The rate at which errors should be injected into the subscriptions.
        :return: A list of subscriptions, some of which are correct and some contain errors.
        """
        subscriptions = self.get_subscriptions(version=subscription_version)

        num_errors = int(len(subscriptions) * error_rate)  
        indices_to_change = random.sample(range(len(subscriptions)), num_errors)

        subscriptions_with_errors = []
        for i, subscription in enumerate(subscriptions):
                if i in indices_to_change:
                    noise_subscription = self.inject_noise(subscription["subscription"], noise_rate=0.1)
                    subscriptions_with_errors.append({
                        "subscription_id": subscription["subscription_id"],
                        "subscription": noise_subscription
                    })
                else:
                    subscriptions_with_errors.append(subscription)

        return subscriptions_with_errors

    def get_publications_with_errors(self, publication_version="json", error_rate=0.1):
        """
        Fetches publications and subs and randomly injects noise into a publication row based on error_rate.
        :param publication_version: Format type ('json' or 'semi').
        :param error_rate: Fraction of publications to change (0.1 = 10%).
        :return: List of publication with noise.
        """
        publications = self.get_publications_with_subscription_matches(limit=1000, publication_version=publication_version, subscription_version="sql")

        total = len(publications)
        num_errors = int(total * error_rate)
        error_indices = set(random.sample(range(total), num_errors))

        results = []
        for i, pub in enumerate(publications):
            if i in error_indices:
                noise_publication = self.inject_noise(pub["publication"], noise_rate=0.1)
                results.append({
                    "publication_id": pub["publication_id"],
                    "publication": noise_publication,
                    "subscription_matches": pub.get("subscription_matches", [])
                })
            else:
                results.append(pub)
        return results


    def decode_blob_to_identifiers(self, blob):
        """
        Decodes a BLOB (8-byte integer) to extract active subscription bit positions.

        Args:
            blob (bytes): The 8-byte BLOB representing a 64-bit bitmask.

        Returns:
            list: A list of integers representing active bit positions (0-63) where bits are set to 1.
        """
        if blob is None:
            return []
        
        # Ensure the blob is in bytes format
        if isinstance(blob, str):
            blob = bytes(blob, 'latin1')  # Use 'latin1' encoding to keep byte values unchanged
        
        # Convert the BLOB to a 64-bit integer
        bitmask = int.from_bytes(blob, byteorder='big')

        # Identify active bit positions
        identifiers = [i for i in range(64) if bitmask & (1 << i)]
        return identifiers

    def save_to_json(self, data, filename):
        """
        Saves the provided data to a JSON file.

        Args:
            data (Any): The data to save.
            filename (str): The name of the file to save the data into.
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Data successfully saved to {filename}")
        except IOError as e:
            print(f"An error occurred while saving to {filename}: {e}")


if __name__ == "__main__":
    database = "smartcampus.db"
    number_of_publications = 100


    with DBHandler(database) as db:
        sql_subs = db.get_subscriptions("sql")
        nlp_subs = db.get_subscriptions("nlp")
        rand_pubs_subs = db.get_publications_with_subscription_matches(number_of_publications,"json")
        rand_subs_with_errors = db.get_subscriptions_with_errors(subscription_version="sql", error_rate=0.1)
        rand_pubs_with_errors = db.get_publications_with_errors("json", error_rate=0.1)

        # Save to JSON

        dir = "smartcampus"

        db.save_to_json(sql_subs, f"{dir}/sql_subscriptions.json")
        db.save_to_json(nlp_subs, f"{dir}/nlp_subscriptions.json")
        db.save_to_json(rand_pubs_subs, f"{dir}/publications_100.json")
        db.save_to_json(rand_subs_with_errors, f"{dir}/subscriptions_with_errors.json")
        db.save_to_json(rand_pubs_with_errors, f"{dir}/publications_with_errors.json")