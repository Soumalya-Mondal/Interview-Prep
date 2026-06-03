# define "db_table_create" function to create SQLite database and table
def db_table_create(database_file_path: str) -> dict[str, str]:
    # Importing Python Module:S1
    try:
        import sqlite3
        from pathlib import Path
    except Exception as error:
        return {'status': 'ERROR', 'step': '1', 'file_name': 'DB-Table-Create', 'message': str(error)}

    # Validate Database Directory:S2
    try:
        # validate if database directory exists, if not create it
        database_file_path_obj = Path(database_file_path)
        database_directory = database_file_path_obj.parent
        
        if not database_directory.exists():
            database_directory.mkdir(parents = True, exist_ok = True)
    except Exception as error:
        return {'status': 'ERROR', 'step': '2', 'file_name': 'DB-Table-Create', 'message': str(error)}

    # Create Database Connection And Cursor:S3
    try:
        # create database connection and cursor
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
    except Exception as error:
        return {'status': 'ERROR', 'step': '3', 'file_name': 'DB-Table-Create', 'message': str(error)}

    # Create SQLite Database And Table:S4
    try:
        # create table if it doesn't exist using connection
        create_table_query = """
        CREATE TABLE IF NOT EXISTS interview_qa_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actual_question_text TEXT NOT NULL DEFAULT 'N/A',
            final_question_text TEXT NOT NULL DEFAULT 'N/A',
            answer_text TEXT NOT NULL DEFAULT 'N/A',
            input_token INTEGER NOT NULL DEFAULT 0,
            output_token INTEGER NOT NULL DEFAULT 0,
            row_inserted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT DEFAULT 'N/A'
        )
        """
        # execute the create table query and commit the changes
        database_cursor.execute(create_table_query)
        database_connection.commit()
        # close the database connection and return success message
        database_connection.close()
        return {'status': 'SUCCESS', 'step': '4', 'file_name': 'DB-Table-Create', 'message': 'SQLite Database And Table Created Successfully'}
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '4', 'file_name': 'DB-Table-Create', 'message': str(error)}