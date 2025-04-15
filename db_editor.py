import sqlite3
import re

def update_subscription_texts(db_path):
    """
    Replaces all occurrences of 'advertisement' with 'publication'
    in the 'sql_subscription' column of the subscriptions table.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch all subscriptions
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

        conn.commit()
        print(f"Updated {updated_count} subscription(s) to replace 'advertisement' with 'publication'.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.close()

def print_all_subscriptions(db_path, version):
    """
    Prints all subscriptions from the subscriptions table.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(f"SELECT id, {version}_subscription FROM subscriptions;")
        subscriptions = cursor.fetchall()

        print(f"\nSubscriptions ({len(subscriptions)} total):\n")
        for sub_id, text in subscriptions:
            print(f"ID {sub_id}: {text}\n")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.close()

def clean_sql_quotes(sql):
    """
    Removes unnecessary double quotes from identifiers in CREATE TABLE statements.
    Keeps quotes around values and keywords if needed.
    """
    # Only target quoted identifiers, not values (e.g., in default 'text' or CHECKs)
    def replacer(match):
        identifier = match.group(1)
        # Don't unquote keywords or strings that require quotes
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            return identifier
        return f'"{identifier}"'  # Keep quote if identifier is weird

    # Replace "identifier" with identifier when safe
    cleaned_sql = re.sub(r'"([^"]+)"', replacer, sql)
    return cleaned_sql.strip()

def save_db_schema_to_file(db_path, file_path="schema.sql"):
    """
    Save the cleaned schema of an SQLite database to a file.

    Args:
        db_path (str): Path to the SQLite database file.
        file_path (str): Path to the file where the schema will be saved.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
            schema_data = cursor.fetchall()

            with open(file_path, "w") as schema_file:
                for table_schema in schema_data:
                    if table_schema[0]:  # Not None
                        cleaned_sql = clean_sql_quotes(table_schema[0])
                        schema_file.write(f"{cleaned_sql};\n\n")
        print(f"Cleaned schema saved to {file_path}")
    except Exception as e:
        print(f"An error occurred while saving the schema: {e}")

def rename_table(db_path, current_name, new_name):
    """
    Rename a table in the SQLite database.

    Args:
        db_path (str): Path to the SQLite database file.
        current_name (str): Current name of the table.
        new_name (str): New name for the table.

    Raises:
        ValueError: If the new table name is invalid or already exists.
    """
    try:
        # Connect to the SQLite database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Check if the current table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (current_name,))
            if not cursor.fetchone():
                raise ValueError(f"Table '{current_name}' does not exist in the database.")

            # Check if the new table name is already in use
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (new_name,))
            if cursor.fetchone():
                raise ValueError(f"A table with the name '{new_name}' already exists.")

            # Rename the table
            cursor.execute(f"ALTER TABLE {current_name} RENAME TO {new_name};")
            print(f"Table '{current_name}' has been renamed to '{new_name}'.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except ValueError as ve:
        print(f"Value error: {ve}")



import sqlite3

def rename_column(db_path, table_name, old_column_name, new_column_name, vacuum_after=False):
    """
    Rename a column in an SQLite table, using native ALTER TABLE if possible.
    Falls back to table rebuild for older SQLite versions. Preserves indexes.

    Args:
        db_path (str): Path to the SQLite database file.
        table_name (str): Name of the table containing the column.
        old_column_name (str): Current name of the column to be renamed.
        new_column_name (str): New name for the column.
        vacuum_after (bool): Whether to run VACUUM after the operation.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Flush WAL log if needed
            cursor.execute("PRAGMA wal_checkpoint(FULL);")

            # Check SQLite version
            sqlite_version = tuple(map(int, sqlite3.sqlite_version.split('.')))
            supports_alter_rename = sqlite_version >= (3, 25, 0)

            # Get the table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            if old_column_name not in column_names:
                raise ValueError(f"Column '{old_column_name}' does not exist in table '{table_name}'.")

            if supports_alter_rename:
                # Fast path: SQLite supports ALTER TABLE RENAME COLUMN
                cursor.execute(
                    f'ALTER TABLE "{table_name}" RENAME COLUMN "{old_column_name}" TO "{new_column_name}";'
                )
                print(f"✅ Fast rename: '{old_column_name}' → '{new_column_name}' using native ALTER TABLE.")
            else:
                # Manual fallback: rebuild the table
                print("⚠️ SQLite version too old — rebuilding table...")

                # Create the new schema
                new_schema = []
                for col in columns:
                    name = new_column_name if col[1] == old_column_name else col[1]
                    new_schema.append(f'"{name}" {col[2]}')
                new_schema_sql = ", ".join(new_schema)

                temp_table = f"{table_name}_temp"
                cursor.execute(f'CREATE TABLE "{temp_table}" ({new_schema_sql});')

                # Copy the data over
                select_columns = [f'"{name}"' for name in column_names]
                select_columns = [
                    f'"{new_column_name}"' if name == old_column_name else name
                    for name in select_columns
                ]
                cursor.execute(
                    f'INSERT INTO "{temp_table}" SELECT {", ".join(select_columns)} FROM "{table_name}";'
                )

                # Recreate indexes
                cursor.execute(
                    f"SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='{table_name}';"
                )
                indexes = cursor.fetchall()

                # Drop the old table and rename the new one
                cursor.execute(f'DROP TABLE "{table_name}";')
                cursor.execute(f'ALTER TABLE "{temp_table}" RENAME TO "{table_name}";')

                # Recreate the indexes (adjusting the column name)
                for index_name, index_sql in indexes:
                    if index_sql:
                        adjusted_sql = index_sql.replace(old_column_name, new_column_name)
                        cursor.execute(adjusted_sql)

                print(f"✅ Column '{old_column_name}' renamed to '{new_column_name}' via table rebuild.")

            if vacuum_after:
                cursor.execute("VACUUM;")
                print("🧹 VACUUM completed.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except ValueError as ve:
        print(f"Value error: {ve}")


def add_timestamp_index(db_path, index_name="idx_events_timestamp"):
    """
    Add an index on the `timestamp` column of the `events` table in an SQLite database.

    Args:
        db_path (str): Path to the SQLite database file.
        index_name (str): Name of the index to be created. Default is 'idx_events_timestamp'.
    """
    try:
        # Connect to the SQLite database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # SQL to create the index
            create_index_query = f"CREATE INDEX IF NOT EXISTS {index_name} ON events (timestamp);"
            cursor.execute(create_index_query)
            conn.commit()
            print(f"Index '{index_name}' added on the `timestamp` column of the `events` table.")
    except Exception as e:
        print(f"An error occurred while adding the index: {e}")


def analyze_and_optimize(db_path):
    """
    Analyzes and optimizes an SQLite database.

    Parameters:
        db_path (str): Path to the SQLite database file.

    Returns:
        dict: Results of the integrity check and status of the optimization.
    """
    results = {}
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Run integrity check
        cursor.execute("PRAGMA integrity_check;")
        integrity_result = cursor.fetchone()[0]
        results['integrity_check'] = integrity_result
        
        if integrity_result != 'ok':
            results['message'] = "Database integrity check failed. Manual inspection required."
        else:
            # Run optimization
            cursor.execute("PRAGMA optimize;")
            results['message'] = "Database integrity check passed, and optimization completed successfully."
        
    except sqlite3.Error as e:
        results['error'] = str(e)
    finally:
        # Close the connection
        if conn:
            conn.close()
    
    return results

def add_index(db_path, table_name, column_name, index_name):
    """
    Adds an index to a specified column in a table.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name});")
        conn.commit()
        print(f"Index {index_name} on {column_name} created successfully.")
    except sqlite3.Error as e:
        print(f"Error creating index: {e}")
    finally:
        conn.close()

def add_primary_key(db_path, table_name, column_name):
    """
    Recreates a table to add a PRIMARY KEY constraint to a column.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Fetch the current schema
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        # Build new schema with PRIMARY KEY
        new_columns = []
        for col in columns:
            col_def = f"{col[1]} {col[2]}"  # Column name and type
            if col[1] == column_name:
                col_def += " PRIMARY KEY"
            if col[3]:  # If column is NOT NULL
                col_def += " NOT NULL"
            new_columns.append(col_def)
        new_schema = ", ".join(new_columns)
        
        # Rename old table, create new table, migrate data, and drop old table
        cursor.execute(f"ALTER TABLE {table_name} RENAME TO {table_name}_old;")
        cursor.execute(f"CREATE TABLE {table_name} ({new_schema});")
        cursor.execute(f"INSERT INTO {table_name} SELECT * FROM {table_name}_old;")
        cursor.execute(f"DROP TABLE {table_name}_old;")
        conn.commit()
        print(f"Added PRIMARY KEY to {column_name} in {table_name}.")
    except sqlite3.Error as e:
        print(f"Error adding primary key: {e}")
    finally:
        conn.close()

def rebuild_indexes_and_vacuum(db_path):
    """
    Rebuilds all indexes and performs a VACUUM operation to optimize the database.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("REINDEX;")
        cursor.execute("VACUUM;")
        conn.commit()
        print("Indexes rebuilt and database vacuumed successfully.")
    except sqlite3.Error as e:
        print(f"Error during index rebuild or vacuum: {e}")
    finally:
        conn.close()

def analyze_database(db_path):
    """
    Runs the ANALYZE command to update statistics for the query planner.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("ANALYZE;")
        conn.commit()
        print("Database analyzed successfully.")
    except sqlite3.Error as e:
        print(f"Error analyzing database: {e}")
    finally:
        conn.close()


def drop_column_from_table(db_path, table_name, column_to_remove):
    """
    Drops a column from an SQLite table by recreating the table without it.

    Args:
        db_path (str): Path to the SQLite database file.
        table_name (str): Name of the table to modify.
        column_to_remove (str): The column name to be dropped.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Get existing table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_info = cursor.fetchall()

            # Extract column names except the one to remove
            columns_to_keep = [col[1] for col in columns_info if col[1] != column_to_remove]
            if column_to_remove not in [col[1] for col in columns_info]:
                raise ValueError(f"Column '{column_to_remove}' does not exist in table '{table_name}'.")

            if not columns_to_keep:
                raise ValueError("Cannot remove the only column in the table.")

            # Build new schema SQL
            new_schema_parts = [f"{col[1]} {col[2]}" for col in columns_info if col[1] != column_to_remove]
            new_schema_sql = ", ".join(new_schema_parts)

            temp_table = f"{table_name}_temp"

            # 1. Create new table without the removed column
            cursor.execute(f'CREATE TABLE "{temp_table}" ({new_schema_sql});')

            # 2. Copy data from old table to new table
            columns_sql = ", ".join(f'"{col}"' for col in columns_to_keep)
            cursor.execute(f'INSERT INTO "{temp_table}" ({columns_sql}) SELECT {columns_sql} FROM "{table_name}";')

            # 3. Drop the old table
            cursor.execute(f'DROP TABLE "{table_name}";')

            # 4. Rename the new table to original name
            cursor.execute(f'ALTER TABLE "{temp_table}" RENAME TO "{table_name}";')

            print(f"✅ Column '{column_to_remove}' successfully removed from table '{table_name}'.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except ValueError as ve:
        print(f"Value error: {ve}")


db_path= "smartcampus.db"

# Add missing index
#print("ADDING INDEX")
#add_index(db_path, table_name="events", column_name="timestamp_unix", index_name="idx_timestamp_unix")
print("")
# Add primary key to subscriptions table
#print("ADDING PRIMARY KEY")
#add_primary_key(db_path, table_name="subscriptions", column_name="id")
print("")
# Rebuild indexes and vacuum database
#print("REBUILD INDEXES AND VACUUM")
#rebuild_indexes_and_vacuum(db_path)
#print("")
# Analyze the database
#print("ANALYZING DATABASE")
#analyze_database(db_path)
print("")
update_subscription_texts(db_path=db_path)

print("SAVING SCHEMA")
print_all_subscriptions(db_path, version="sql")