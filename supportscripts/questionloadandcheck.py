# define "question_load_and_check" function to load questions from file and insert into database table
def question_load_and_check(question_file_path: str, database_file_path: str) -> dict[str, str]:
    # Define Constants
    inserted_questions_dict = {}

    # Importing Python Module:S1
    try:
        import sqlite3
        from pathlib import Path
        import os
        import asyncio
        from openai import AsyncAzureOpenAI
    except Exception as error:
        return {'status': 'ERROR', 'step': '1', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Check File Is Present:S2
    try:
        # validate question file path exists
        question_file_path_obj = Path(question_file_path)
        if not question_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Load-And-Check', 'message': f'Question File Not Found: {question_file_path}'}

        # validate database file path exists
        database_file_path_obj = Path(database_file_path)
        if not database_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Load-And-Check', 'message': f'Database File Not Found: {database_file_path}'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '2', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Load The Question Into Memory:S3
    try:
        # read the question file and load questions into memory
        with open(str(question_file_path), 'r', encoding = 'utf-8') as question_file:
            raw_question_text = [line.strip() for line in question_file.readlines() if line.strip()]

        if not raw_question_text:
            return {'status': 'ERROR', 'step': '3', 'file_name': 'Question-Load-And-Check', 'message': 'No Questions Found In File'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '3', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Create Database Connection:S4
    try:
        # create database connection
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
    except Exception as error:
        return {'status': 'ERROR', 'step': '4', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Insert Questions Into Table:S5
    try:
        # insert each question as a separate row
        for question in raw_question_text:
            insert_query = """
            INSERT INTO interview_qa_table (actual_question_text)
            VALUES (?)
            """
            database_cursor.execute(insert_query, (question,))
            # get the ID of the inserted row and store in dictionary
            inserted_questions_dict[database_cursor.lastrowid] = question

        # commit the changes and close the connection
        database_connection.commit()
        database_connection.close()
        # return success message with count of inserted questions
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '5', 'file_name': 'Question-Load-And-Check', 'message': str(error)}

    # Correct Grammar And Spelling Using Azure OpenAI:S6
    try:
        
        # define async function to call Azure OpenAI
        async def correct_question(question_id: int, question_text: str) -> dict:
            try:
                client = AsyncAzureOpenAI(
                    api_endpoint=os.getenv('API_ENDPOINT'),
                    api_key=os.getenv('API_KEY'),
                    api_version=os.getenv('API_VERSION')
                )
                
                system_prompt = "Check and correct grammar and spelling in the following interview question"
                
                response = await client.chat.completions.create(
                    model=os.getenv('CHAT_MODEL_NAME'),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question_text}
                    ]
                )
                
                corrected_text = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                
                return {
                    'id': question_id,
                    'original_question': question_text,
                    'corrected_question': corrected_text,
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
        
        # define async function to process all questions
        async def process_all_questions():
            corrected_questions_dict = {}
            tasks = [correct_question(q_id, q_text) for q_id, q_text in inserted_questions_dict.items()]
            results = await asyncio.gather(*tasks)
            
            for result in results:
                q_id = result['id']
                if result['status'] == 'SUCCESS':
                    corrected_questions_dict[q_id] = {
                        'original_question': result['original_question'],
                        'corrected_question': result['corrected_question'],
                        'input_tokens': result['input_tokens'],
                        'output_tokens': result['output_tokens'],
                        'model_name': result['model_name']
                    }
                else:
                    # continue with next question if this one fails
                    corrected_questions_dict[q_id] = {
                        'original_question': result['original_question'],
                        'corrected_question': None,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'model_name': result['model_name'],
                        'error': result.get('message', 'Unknown error')
                    }
            
            return corrected_questions_dict
        
        # run async function using asyncio.run()
        corrected_questions_dict = asyncio.run(process_all_questions())
        
        return {'status': 'SUCCESS', 'step': '6', 'file_name': 'Question-Load-And-Check', 'message': 'Questions corrected successfully', 'corrected_questions': corrected_questions_dict}
    except Exception as error:
        return {'status': 'ERROR', 'step': '6', 'file_name': 'Question-Load-And-Check', 'message': str(error)}