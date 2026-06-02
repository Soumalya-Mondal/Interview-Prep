# define main function
if __name__ == "__main__":
    # import python modules:s1
    try:
        from pathlib import Path
        from dotenv import load_dotenv
        import os
        import sqlite3
        from openai import AzureOpenAI
    except Exception as error:
        print(f'ERROR - [Main:S1] - {str(error)}')
        exit(1)

    # define folder path:s2
    try:
        parent_folder_path = Path.cwd()
        input_folder_path = parent_folder_path / 'input'
        output_folder_path = parent_folder_path / 'output'
        database_folder_path = parent_folder_path / 'Database'
        env_file_path = parent_folder_path / '.env'
        system_prompt_file_path = input_folder_path / 'SystemPromptForQuestion.txt'
        question_file_path = input_folder_path / 'InterviewQuestions.txt'
        database_file_path = database_folder_path / 'interview_qa.db'
    except Exception as error:
        print(f'ERROR - [Main:S2] - {str(error)}')
        exit(1)

    # load environment variables:s3
    try:
        if env_file_path.exists():
            load_dotenv(dotenv_path = env_file_path)
            
            # validate required environment variables
            required_credential = ['API_KEY', 'API_VERSION', 'API_ENDPOINT', 'CHAT_MODEL_NAME']
            missing_credential = [var for var in required_credential if not os.getenv(var)]
            
            if missing_credential:
                print(f'ERROR - [Main:S3] - Missing Environment Variables: {", ".join(missing_credential)}')
                exit(1)
            else:
                api_key = os.getenv('API_KEY')
                api_version = os.getenv('API_VERSION')
                api_endpoint = os.getenv('API_ENDPOINT')
                chat_model_name = os.getenv('CHAT_MODEL_NAME')
                print(f'SUCCESS - [Main:S3] - Environment Variables Loaded Successfully')
        else:
            print(f'ERROR - [Main:S3] - ".env" File Not Found: {env_file_path}')
            exit(1)
    except Exception as error:
        print(f'ERROR - [Main:S3] - {str(error)}')
        exit(1)

    # load interview questions from file:s4
    try:
        if question_file_path.exists():
            with open(question_file_path, 'r', encoding = 'utf-8') as question_file:
                questions_list = [line.strip() for line in question_file.readlines() if line.strip()]
        else:
            print(f'ERROR - [Main:S4] - "InterviewQuestions.txt" File Not Found: {question_file_path}')
            questions_list = []
            exit(1)
    except Exception as error:
        print(f'ERROR - [Main:S4] - {str(error)}')
        exit(1)

    # load system prompt if questions list is not empty:s5
    try:
        if questions_list:
            if system_prompt_file_path.exists():
                with open(system_prompt_file_path, 'r', encoding = 'utf-8') as system_prompt_file:
                    question_answer_system_prompt = system_prompt_file.read()
            else:
                print(f'ERROR - [Main:S5] - "SystemPromptForQuestion.txt" File Not Found: {system_prompt_file_path}')
                question_answer_system_prompt = ""
                exit(1)
        else:
            print(f'ERROR - [Main:S5] - Questions List Is Empty')
            question_answer_system_prompt = ""
            exit(1)
    except Exception as error:
        print(f'ERROR - [Main:S5] - {str(error)}')
        exit(1)

    # create database connection and cursor:s6
    try:
        # create database folder if it doesn't exist
        database_folder_path.mkdir(parents = True, exist_ok = True)
        
        # create global database connection and cursor
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
        
        print(f'SUCCESS - [Main:S6] - Database Connection And Cursor Created Successfully')
    except Exception as error:
        print(f'ERROR - [Main:S6] - {str(error)}')
        exit(1)

    # create sqlite database and table:s7
    try:
        # create table if it doesn't exist using global connection
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
        
        print(f'SUCCESS - [Main:S7] - SQLite Table Created Successfully')
    except Exception as error:
        print(f'ERROR - [Main:S7] - {str(error)}')
        database_connection.close()
        exit(1)

    # create and test azure openai client:s8
    try:
        # initialize azure openai client with loaded environment variables
        client = AzureOpenAI(
            api_key = api_key,
            api_version = api_version,
            azure_endpoint = api_endpoint
        )
        
        # verify client object was created
        if client is None:
            print(f'ERROR - [Main:S8] - Failed To Create Azure OpenAI Client')
            database_connection.close()
            exit(1)
        
        # test the client with a simple api call
        test_response = client.chat.completions.create(
            model = chat_model_name,
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Test connection. Reply with: SUCCESS"}
            ],
            temperature = 0.7,
            max_completion_tokens = 10
        )
        
        # verify test response and check for success keyword
        if test_response and test_response.choices and len(test_response.choices) > 0:
            response_content = test_response.choices[0].message.content
            
            # check if response contains "success"
            if response_content and ('success' in response_content.lower()):
                print(f'SUCCESS - [Main:S8] - Azure OpenAI Client Created And Tested Successfully')
            else:
                print(f'ERROR - [Main:S8] - API Validation Failed - Did Not Receive SUCCESS')
                print(f'  Received Response: {response_content}')
                database_connection.close()
                exit(1)
        else:
            print(f'ERROR - [Main:S8] - Client Test Call Failed - No Response')
            database_connection.close()
            exit(1)
    except Exception as error:
        print(f'ERROR - [Main:S8] - {str(error)}')
        database_connection.close()
        exit(1)

    # process questions with azure openai and store in database
    if questions_list and question_answer_system_prompt:
        # loop through questions and process each one
        for index, question in enumerate(questions_list, start = 1):
            # call azure openai api for answer:s9
            try:
                response = client.chat.completions.create(
                    model = chat_model_name,
                    messages = [
                        {"role": "system", "content": question_answer_system_prompt},
                        {"role": "user", "content": question}
                    ],
                    temperature = 0.7
                )
                
                # extract answer and token usage
                answer = response.choices[0].message.content
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
            except Exception as error:
                print(f'ERROR - [Main:S9] - {str(error)}')
                database_connection.close()
                exit(1)
                
            # insert into database using global connection:s10
            try:
                database_cursor.execute(
                    "INSERT INTO interview_qa_table (question_text, answer_text, input_token, output_token, model_name) VALUES (?, ?, ?, ?, ?)",
                    (question, answer, prompt_tokens, completion_tokens, chat_model_name)
                )
                database_connection.commit()
                
                print(f'SUCCESS - [Main:S10] - Inserted "Q{index}" into database')
            except Exception as db_error:
                print(f'ERROR - [Main:S10] - Database Insert Failed For Q{index}: {str(db_error)}')
                database_connection.close()
                exit(1)
        
        # close database connection after all questions processed:s11
        try:
            database_connection.close()
            print(f'SUCCESS - [Main:S11] - All Questions Processed And Database Connection Closed')
        except Exception as error:
            print(f'ERROR - [Main:S11] - {str(error)}')
    else:
        database_connection.close()
        exit(1)