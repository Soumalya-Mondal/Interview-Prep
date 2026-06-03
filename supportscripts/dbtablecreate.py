def db_table_create(database_file_path):
    # Importing Python Module:S1
    try:
        import sqlite3
    except Exception as error:
        return {'status': 'error', 'step': '1', 'file_name': 'DB-Table-Create', 'message': str(error)}

    # Create Database Connection And Cursor:S2
    try:
        # create database connection and cursor
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
        print(f'SUCCESS - Database Connection And Cursor Created Successfully')
    except Exception as error:
        return {'status': 'error', 'step': '2', 'file_name': 'DB-Table-Create', 'message': str(error)}

    # Create SQLite Database And Table:S3
    try:
        # create table if it doesn't exist using connection
        create_table_query = """
        CREATE TABLE IF NOT EXISTS interview_qa_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL DEFAULT 'N/A',
            answer_text TEXT NOT NULL DEFAULT 'N/A',
            input_token INTEGER NOT NULL DEFAULT 0,
            output_token INTEGER NOT NULL DEFAULT 0,
            row_inserted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT DEFAULT 'N/A'
        )
        """
        database_cursor.execute(create_table_query)
        database_connection.commit()
        return {'status': 'success', 'step': '3', 'file_name': 'DB-Table-Create', 'message': 'SQLite Database And Table Created Successfully'}
    except Exception as error:
        return {'status': 'error', 'step': '3', 'file_name': 'DB-Table-Create', 'message': str(error)}