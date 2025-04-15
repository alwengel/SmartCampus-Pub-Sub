import sqlite3
import re
import json

class SQLiteManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def update_subscription_texts(self):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, sql_subscription FROM subscriptions;")
                subscriptions = cursor.fetchall()
                updated_count = 0

                for sub_id, text in subscriptions:
                    if text and "advertisement" in text:
                        new_text = text.replace("advertisement", "publication")
                        cursor.execute(
                            "UPDATE subscriptions SET sql_subscription = ? WHERE id = ?;",
                            (new_text, sub_id)
                        )
                        updated_count += 1
                print(f"Updated {updated_count} subscription(s).")
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")

    def print_all_subscriptions(self, version):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT id, {version}_subscription FROM subscriptions;")
                subscriptions = cursor.fetchall()
                print(f"\nSubscriptions ({len(subscriptions)} total):\n")
                for sub_id, text in subscriptions:
                    print(f"ID {sub_id}: {text}\n")
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")

    def clean_sql_quotes(self, sql):
        def replacer(match):
            identifier = match.group(1)
            return identifier if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier) else f'"{identifier}"'
        return re.sub(r'"([^"]+)"', replacer, sql).strip()

    def save_schema(self, file_path="schema.sql"):
        try:
            with self._connect() as conn, open(file_path, "w") as schema_file:
                cursor = conn.cursor()
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
                for (table_schema,) in cursor.fetchall():
                    if table_schema:
                        cleaned_sql = self.clean_sql_quotes(table_schema)
                        schema_file.write(f"{cleaned_sql};\n\n")
            print(f"Schema saved to {file_path}")
        except Exception as e:
            print(f"Error saving schema: {e}")

    def rename_table(self, current_name, new_name):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (current_name,))
                if not cursor.fetchone():
                    raise ValueError(f"Table '{current_name}' does not exist.")
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (new_name,))
                if cursor.fetchone():
                    raise ValueError(f"Table '{new_name}' already exists.")
                cursor.execute(f"ALTER TABLE {current_name} RENAME TO {new_name};")
                print(f"Renamed '{current_name}' to '{new_name}'.")
        except (sqlite3.Error, ValueError) as e:
            print(f"Error: {e}")

    def rename_column(self, table_name, old_col, new_col, vacuum=False):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA wal_checkpoint(FULL);")
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                col_names = [col[1] for col in columns]

                if old_col not in col_names:
                    raise ValueError(f"Column '{old_col}' not found.")

                if sqlite3.sqlite_version_info >= (3, 25, 0):
                    cursor.execute(
                        f'ALTER TABLE "{table_name}" RENAME COLUMN "{old_col}" TO "{new_col}";'
                    )
                    print(f"Renamed column '{old_col}' to '{new_col}'.")
                else:
                    # Rebuild logic omitted for brevity
                    print("Old SQLite version: manual rebuild required.")
                if vacuum:
                    cursor.execute("VACUUM;")
        except (sqlite3.Error, ValueError) as e:
            print(f"Error: {e}")

    def add_index(self, table, column, index_name):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column});")
                conn.commit()
                print(f"Index '{index_name}' created.")
        except sqlite3.Error as e:
            print(f"Error creating index: {e}")

    def add_primary_key(self, table, column):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table});")
                columns = cursor.fetchall()
                new_columns = []
                for col in columns:
                    definition = f"{col[1]} {col[2]}"
                    if col[1] == column:
                        definition += " PRIMARY KEY"
                    if col[3]:
                        definition += " NOT NULL"
                    new_columns.append(definition)

                cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old;")
                cursor.execute(f"CREATE TABLE {table} ({', '.join(new_columns)});")
                cursor.execute(f"INSERT INTO {table} SELECT * FROM {table}_old;")
                cursor.execute(f"DROP TABLE {table}_old;")
                conn.commit()
                print(f"Primary key added to '{column}'.")
        except sqlite3.Error as e:
            print(f"Error adding primary key: {e}")

    def rebuild_indexes_and_vacuum(self):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("REINDEX;")
                cursor.execute("VACUUM;")
                conn.commit()
                print("Rebuilt indexes and vacuumed.")
        except sqlite3.Error as e:
            print(f"Error: {e}")

    def analyze(self):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("ANALYZE;")
                conn.commit()
                print("Database analyzed.")
        except sqlite3.Error as e:
            print(f"Error: {e}")

    def analyze_and_optimize(self):
        results = {}
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                result = cursor.fetchone()[0]
                results['integrity_check'] = result
                if result == "ok":
                    cursor.execute("PRAGMA optimize;")
                    results['message'] = "Optimization complete."
                else:
                    results['message'] = "Integrity check failed."
        except sqlite3.Error as e:
            results['error'] = str(e)
        return results

    def drop_column(self, table, column_to_remove):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table});")
                columns = cursor.fetchall()
                keep_cols = [col for col in columns if col[1] != column_to_remove]

                if not keep_cols:
                    raise ValueError("Cannot remove the only column.")

                temp_table = f"{table}_temp"
                schema = ", ".join([f"{col[1]} {col[2]}" for col in keep_cols])
                cursor.execute(f'CREATE TABLE "{temp_table}" ({schema});')

                col_names = ", ".join(f'"{col[1]}"' for col in keep_cols)
                cursor.execute(f'INSERT INTO "{temp_table}" ({col_names}) SELECT {col_names} FROM "{table}";')

                cursor.execute(f'DROP TABLE "{table}";')
                cursor.execute(f'ALTER TABLE "{temp_table}" RENAME TO "{table}";')
                print(f"Column '{column_to_remove}' removed from '{table}'.")
        except (sqlite3.Error, ValueError) as e:
            print(f"Error: {e}")

    def add_running_id_to_publications(self):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(publications);")
                columns = cursor.fetchall()
                if "id" in [col[1] for col in columns]:
                    print("'id' column already exists.")
                    return

                print("Rebuilding 'publications' with 'id' PRIMARY KEY.")
                schema = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
                for col in columns:
                    col_def = f"{col[1]} {col[2]}"
                    if col[3]:
                        col_def += " NOT NULL"
                    schema.append(col_def)

                temp_table = "publications_temp"
                cursor.execute(f"CREATE TABLE {temp_table} ({', '.join(schema)});")

                col_names = ", ".join(f'"{col[1]}"' for col in columns)
                cursor.execute(
                    f"INSERT INTO {temp_table} ({col_names}) SELECT {col_names} FROM publications;"
                )

                cursor.execute("DROP TABLE publications;")
                cursor.execute(f"ALTER TABLE {temp_table} RENAME TO publications;")
                print("Added 'id' PRIMARY KEY to publications.")
        except sqlite3.Error as e:
            print(f"Error: {e}")

    def clean_up_database(self):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS publication_matches;")
                print("Cleanup complete.")
        except sqlite3.Error as e:
            print(f"Error during cleanup: {e}")


if __name__=="__main__":
    db = SQLiteManager("smartcampus.db")
    db.save_schema()