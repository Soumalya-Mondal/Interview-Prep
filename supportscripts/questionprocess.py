# define "question_process" function to fetch and process questions with Azure OpenAI
def question_process(database_file_path: str, system_prompt_file_path: str) -> dict[str, str]:
    # Importing Python Modules: S1
    try:
        import sqlite3
        from pathlib import Path
        import os
        import json
        from openai import AzureOpenAI
    except Exception as error:
        return {'status': 'ERROR', 'step': '1', 'file_name': 'Question-Process', 'message': str(error)}

    # Check Files Are Present And Load System Prompt: S2
    try:
        # validate database file path exists
        database_file_path_obj = Path(database_file_path)
        if not database_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Process', 'message': f'Database File Not Found: {database_file_path}'}
        
        # validate system prompt file path exists
        system_prompt_file_path_obj = Path(system_prompt_file_path)
        if not system_prompt_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Process', 'message': f'System Prompt File Not Found: {system_prompt_file_path}'}
        
        # read the system prompt file and load into memory
        with open(str(system_prompt_file_path), 'r', encoding='utf-8') as system_prompt_file:
            system_prompt = system_prompt_file.read().strip()
        
        if not system_prompt:
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Process', 'message': 'System Prompt File Is Empty'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Process', 'message': str(error)}

    # Create Database Connection: S3
    try:
        # create database connection
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
    except Exception as error:
        return {'status': 'ERROR', 'step': '3', 'file_name': 'Question-Process', 'message': str(error)}

    # Fetch Questions From Database: S4
    try:
        # fetch all questions where row_status = 1 (Data inserted)
        fetch_query = """
        SELECT id, actual_question_text FROM interview_qa_table 
        WHERE row_status = 1
        ORDER BY id ASC
        """
        database_cursor.execute(fetch_query)
        questions_to_process = database_cursor.fetchall()
        
        if not questions_to_process:
            database_connection.close()
            return {'status': 'ERROR', 'step': '4', 'file_name': 'Question-Process', 'message': 'No questions found with row_status = 1'}
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '4', 'file_name': 'Question-Process', 'message': str(error)}

    # Define Azure OpenAI Client: S5
    try:
        client = AzureOpenAI(
            azure_endpoint=os.getenv('API_ENDPOINT'),
            api_key=os.getenv('API_KEY'),
            api_version=os.getenv('API_VERSION'),
            timeout=30.0
        )
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '5', 'file_name': 'Question-Process', 'message': f'Azure OpenAI Client Init Failed: {str(error)}'}
    
    # Process Questions Sequentially: S6
    try:
        import time
        max_retries = 3
        base_delay = 1
        
        processed_questions_dict = {}
        
        for question_id, question_text in questions_to_process:
            try:
                # Call Azure OpenAI API with retry logic
                response = None
                for attempt in range(max_retries):
                    try:
                        # prepare JSON payload with id and question
                        json_payload = json.dumps({"id": question_id, "question": question_text})
                        
                        response = client.chat.completions.create(
                            model=os.getenv('CHAT_MODEL_NAME'),
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": json_payload}
                            ],
                            timeout=30.0
                        )
                        break  # Success, exit retry loop
                    except Exception as retry_error:
                        if attempt < max_retries - 1:
                            wait_time = base_delay * (2 ** attempt)
                            print(f"WARNING - Question ID {question_id}: Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                        else:
                            raise retry_error
                
                if response is None:
                    raise Exception("Failed to get response after retries")
                
                processed_text = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                
                # parse JSON response to extract processed question
                try:
                    response_json = json.loads(processed_text)
                    processed_question_text = response_json.get('question', processed_text)
                except (json.JSONDecodeError, TypeError):
                    # if response is not valid JSON, use it as-is
                    processed_question_text = processed_text
                
                processed_questions_dict[question_id] = {
                    'id': question_id,
                    'original_question': question_text,
                    'processed_question': processed_question_text,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'model_name': os.getenv('CHAT_MODEL_NAME'),
                    'status': 'SUCCESS'
                }
                
                # Print success message immediately after processing each question
                print(f"SUCCESS - Question ID: {question_id}; Input Tokens = {input_tokens}, Output Tokens = {output_tokens}")
            
            except Exception as error:
                database_connection.close()
                return {'status': 'ERROR', 'step': '6', 'file_name': 'Question-Process', 'message': f'Error processing Question ID {question_id}: {str(error)}'}
    
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '6', 'file_name': 'Question-Process', 'message': str(error)}
    
    # Update Database With Processed Questions And Cumulative Tokens: S7
    try:
        for q_id, result in processed_questions_dict.items():
            if result['status'] == 'SUCCESS':
                # fetch current token values to calculate cumulative sum
                get_tokens_query = "SELECT input_token, output_token FROM interview_qa_table WHERE id = ?"
                database_cursor.execute(get_tokens_query, (q_id,))
                token_row = database_cursor.fetchone()
                current_input_tokens = token_row[0] if token_row else 0
                current_output_tokens = token_row[1] if token_row else 0
                
                # calculate cumulative tokens (add new tokens to existing)
                new_input_tokens = current_input_tokens + result['input_tokens']
                new_output_tokens = current_output_tokens + result['output_tokens']
                
                # update database with processed question and cumulative tokens
                update_query = """
                UPDATE interview_qa_table 
                SET final_question_text = ?, 
                    input_token = ?, 
                    output_token = ?, 
                    model_name = ?,
                    row_status = 2
                WHERE id = ?
                """
                database_cursor.execute(update_query, (
                    result['processed_question'],
                    new_input_tokens,
                    new_output_tokens,
                    result['model_name'],
                    q_id
                ))
            else:
                pass
        
        database_connection.commit()
        database_connection.close()
        
        return {'status': 'SUCCESS', 'file_name': 'Question-Process', 'message': ''}
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '7', 'file_name': 'Question-Process', 'message': str(error)}
