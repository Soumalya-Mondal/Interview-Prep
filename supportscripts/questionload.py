# define "question_load" function to load questions from file and insert into database
def question_load(question_file_path: str, database_file_path: str) -> dict[str, str]:
    # Importing Python Modules: S1
    try:
        import sqlite3
        from pathlib import Path
    except Exception as error:
        return {'status': 'ERROR', 'step': '1', 'file_name': 'Question-Load', 'message': str(error)}

    # Check Files Are Present: S2
    try:
        # validate question file path exists
        question_file_path_obj = Path(question_file_path)
        if not question_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Load', 'message': f'Question File Not Found: {question_file_path}'}

        # validate database file path exists
        database_file_path_obj = Path(database_file_path)
        if not database_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Load', 'message': f'Database File Not Found: {database_file_path}'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Load', 'message': str(error)}

    # Load Questions Into Memory: S3
    try:
        # read the question file and load questions into memory
        with open(str(question_file_path), 'r', encoding='utf-8') as question_file:
            raw_question_text = [line.strip() for line in question_file.readlines() if line.strip()]

        if not raw_question_text:
            return {'status': 'ERROR', 'step': '3', 'file_name': 'Question-Load', 'message': 'No Questions Found In File'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '3', 'file_name': 'Question-Load', 'message': str(error)}

    # Create Database Connection: S4
    try:
        # create database connection
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
    except Exception as error:
        return {'status': 'ERROR', 'step': '4', 'file_name': 'Question-Load', 'message': str(error)}

    # Insert Raw Questions Into Table: S5
    try:
        # insert each question as a separate row with row_status = 1 (Data inserted)
        for question in raw_question_text:
            insert_query = """
            INSERT INTO interview_qa_table (actual_question_text, row_status)
            VALUES (?, 1)
            """
            database_cursor.execute(insert_query, (question,))

        # commit the changes
        database_connection.commit()
        database_connection.close()
        
        return {'status': 'SUCCESS', 'file_name': 'Question-Load', 'message': f'Successfully Loaded {len(raw_question_text)} Questions Into Database With'}
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '5', 'file_name': 'Question-Load', 'message': str(error)}
