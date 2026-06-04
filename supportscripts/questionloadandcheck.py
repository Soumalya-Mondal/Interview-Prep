# define "question_load_and_check" function to load questions from file, insert into database, fetch unanswered questions, and process with Azure OpenAI
def question_load_and_check(question_file_path: str, database_file_path: str, system_prompt_file_path: str) -> dict[str, str]:
    # Importing Python Modules: S1
    try:
        import sqlite3
        from pathlib import Path
        import os
        import asyncio
        import json
        from openai import AsyncAzureOpenAI
    except Exception as error:
        return {'status': 'ERROR', 'step': '1', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Check Files Are Present: S2
    try:
        # validate question file path exists
        question_file_path_obj = Path(question_file_path)
        if not question_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Load-And-Check', 'message': f'Question File Not Found: {question_file_path}'}

        # validate database file path exists
        database_file_path_obj = Path(database_file_path)
        if not database_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Load-And-Check', 'message': f'Database File Not Found: {database_file_path}'}
        
        # validate system prompt file path exists
        system_prompt_file_path_obj = Path(system_prompt_file_path)
        if not system_prompt_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Load-And-Check', 'message': f'System Prompt File Not Found: {system_prompt_file_path}'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Load Questions And System Prompt Into Memory: S3
    try:
        # read the question file and load questions into memory
        with open(str(question_file_path), 'r', encoding='utf-8') as question_file:
            raw_question_text = [line.strip() for line in question_file.readlines() if line.strip()]

        if not raw_question_text:
            return {'status': 'ERROR', 'step': '3', 'file_name': 'Question-Load-And-Check', 'message': 'No Questions Found In File'}
        
        # read the system prompt file and load into memory
        with open(str(system_prompt_file_path), 'r', encoding='utf-8') as system_prompt_file:
            system_prompt = system_prompt_file.read().strip()
        
        if not system_prompt:
            return {'status': 'ERROR', 'step': '3', 'file_name': 'Question-Load-And-Check', 'message': 'System Prompt File Is Empty'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '3', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Create Database Connection: S4
    try:
        # create database connection
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
    except Exception as error:
        return {'status': 'ERROR', 'step': '4', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Insert Raw Questions Into Table: S5
    try:
        # insert each question as a separate row with status 'Not Processed'
        for question in raw_question_text:
            insert_query = """
            INSERT INTO interview_qa_table (actual_question_text, status)
            VALUES (?, 'Not Processed')
            """
            database_cursor.execute(insert_query, (question,))

        # commit the changes
        database_connection.commit()
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '5', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Fetch Unanswered Questions From Database: S6
    try:
        # fetch all questions where final_question_text is still 'N/A' (unanswered)
        fetch_query = """
        SELECT id, actual_question_text FROM interview_qa_table 
        WHERE final_question_text = 'N/A'
        ORDER BY id ASC
        """
        database_cursor.execute(fetch_query)
        unanswered_questions = database_cursor.fetchall()
        
        if not unanswered_questions:
            return {'status': 'ERROR', 'step': '6', 'file_name': 'Question-Load-And-Check', 'message': 'No unanswered questions found in database'}
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '6', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Correct Grammar And Spelling Using Azure OpenAI: S7
    try:
        # define async function to call Azure OpenAI with JSON payload
        async def correct_question(question_id: int, question_text: str) -> dict:
            try:
                client = AsyncAzureOpenAI(
                    azure_endpoint=os.getenv('API_ENDPOINT'),
                    api_key=os.getenv('API_KEY'),
                    api_version=os.getenv('API_VERSION')
                )
                
                # prepare JSON payload with id and question
                json_payload = json.dumps({"id": question_id, "question": question_text})
                
                # use the loaded system prompt from file
                response = await client.chat.completions.create(
                    model=os.getenv('CHAT_MODEL_NAME'),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": json_payload}
                    ]
                )
                
                corrected_text = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                
                # parse JSON response to extract corrected question
                try:
                    response_json = json.loads(corrected_text)
                    corrected_question_text = response_json.get('question', corrected_text)
                except (json.JSONDecodeError, TypeError):
                    # if response is not valid JSON, use it as-is
                    corrected_question_text = corrected_text
                
                return {
                    'id': question_id,
                    'original_question': question_text,
                    'corrected_question': corrected_question_text,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'model_name': os.getenv('CHAT_MODEL_NAME'),
                    'status': 'SUCCESS'
                }
            except Exception as error:
                return {
                    'id': question_id,
                    'original_question': question_text,
                    'corrected_question': None,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'model_name': os.getenv('CHAT_MODEL_NAME'),
                    'status': 'ERROR',
                    'message': str(error)
                }
        
        # define async function to process all questions concurrently
        async def process_all_questions():
            corrected_questions_dict = {}
            tasks = [correct_question(q_id, q_text) for q_id, q_text in unanswered_questions]
            results = await asyncio.gather(*tasks)
            
            for result in results:
                q_id = result['id']
                corrected_questions_dict[q_id] = result
            
            return corrected_questions_dict
        
        # run async function using asyncio.run()
        corrected_questions_dict = asyncio.run(process_all_questions())
    except Exception as error:
        return {'status': 'ERROR', 'step': '7', 'file_name': 'Question-Load-And-Check', 'message': str(error)}
    
    # Update Database With Corrected Questions And Cumulative Tokens: S8
    try:
        for q_id, result in corrected_questions_dict.items():
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
                
                # update database with corrected question and cumulative tokens
                update_query = """
                UPDATE interview_qa_table 
                SET final_question_text = ?, 
                    input_token = ?, 
                    output_token = ?, 
                    model_name = ?
                WHERE id = ?
                """
                database_cursor.execute(update_query, (
                    result['corrected_question'],
                    new_input_tokens,
                    new_output_tokens,
                    result['model_name'],
                    q_id
                ))
            else:
                # skip if processing failed, record remains 'Not Processed'
                pass
        
        database_connection.commit()
        
        return {
            'status': 'SUCCESS', 
            'file_name': 'Question-Load-And-Check', 
            'message': 'All phases completed successfully. Questions inserted and processed.',
            'corrected_questions': corrected_questions_dict
        }
    except Exception as error:
        return {'status': 'ERROR', 'step': '8', 'file_name': 'Question-Load-And-Check', 'message': str(error)}