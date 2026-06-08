# define "question_answer_process" function to fetch and process question answers with Azure OpenAI
def question_answer_process(database_file_path: str, system_prompt_file_path: str) -> dict[str, str]:
    # Importing Python Modules: S1
    try:
        import sqlite3
        from pathlib import Path
        import os
        from openai import AzureOpenAI
    except Exception as error:
        return {'status': 'ERROR', 'step': '1', 'file_name': 'Question-Answer-Process', 'message': str(error)}

    # Check Files Are Present And Load System Prompt: S2
    try:
        # validate database file path exists
        database_file_path_obj = Path(database_file_path)
        if not database_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Answer-Process', 'message': f'Database File Not Found: {database_file_path}'}
        
        # validate system prompt file path exists
        system_prompt_file_path_obj = Path(system_prompt_file_path)
        if not system_prompt_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Answer-Process', 'message': f'System Prompt File Not Found: {system_prompt_file_path}'}
        
        # read the system prompt file and load into memory
        with open(str(system_prompt_file_path), 'r', encoding='utf-8') as system_prompt_file:
            system_prompt = system_prompt_file.read().strip()
        
        if not system_prompt:
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Answer-Process', 'message': 'System Prompt File Is Empty'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Answer-Process', 'message': str(error)}

    # Create Database Connection: S3
    try:
        # create database connection
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
    except Exception as error:
        return {'status': 'ERROR', 'step': '3', 'file_name': 'Question-Answer-Process', 'message': str(error)}

    # Fetch Answers From Database: S4
    try:
        # fetch all answers where row_status = 2 (Processed questions)
        fetch_query = """
        SELECT id, actual_question_text, input_token, output_token FROM interview_qa_table 
        WHERE row_status = 2
        ORDER BY id ASC
        """
        database_cursor.execute(fetch_query)
        answers_to_process = database_cursor.fetchall()
        
        if not answers_to_process:
            database_connection.close()
            return {'status': 'ERROR', 'step': '4', 'file_name': 'Question-Answer-Process', 'message': 'No answers found with row_status = 2'}
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '4', 'file_name': 'Question-Answer-Process', 'message': str(error)}

    # Define function to call Azure OpenAI with JSON payload: S5
    try:
        client = AzureOpenAI(
            azure_endpoint=os.getenv('API_ENDPOINT'),
            api_key=os.getenv('API_KEY'),
            api_version=os.getenv('API_VERSION')
        )
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '5', 'file_name': 'Question-Answer-Process', 'message': str(error)}

    # Process Answers Sequentially With Ladder Logic: S6
    try:
        total_input_tokens = 0
        total_output_tokens = 0
        success_count = 0

        for answer_id, question_text, existing_input_tokens, existing_output_tokens in answers_to_process:
            try:
                # Call Azure OpenAI API
                response = client.chat.completions.create(
                    model=os.getenv('CHAT_MODEL_NAME'),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question_text}
                    ]
                )
                
                # Extract response and token usage
                processed_answer_text = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                
                # Calculate cumulative tokens
                cumulative_input_tokens = existing_input_tokens + input_tokens
                cumulative_output_tokens = existing_output_tokens + output_tokens
                
                # Update database immediately with processed answer and cumulative tokens
                update_query = """
                UPDATE interview_qa_table
                SET answer_text = ?, 
                    input_token = ?, 
                    output_token = ?,
                    row_status = 3
                WHERE id = ?
                """
                database_cursor.execute(
                    update_query,
                    (processed_answer_text, cumulative_input_tokens, cumulative_output_tokens, answer_id)
                )
                database_connection.commit()
                
                success_count += 1
                
            except Exception as error:
                database_connection.close()
                return {
                    'status': 'ERROR',
                    'step': '6',
                    'file_name': 'Question-Answer-Process',
                    'message': str(error)
                }
        
        database_connection.close()
        
        return {
            'status': 'SUCCESS',
            'file_name': 'Question-Answer-Process',
            'message': f'All {success_count} answers processed successfully'
        }
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '6', 'file_name': 'Question-Answer-Process', 'message': str(error)}
