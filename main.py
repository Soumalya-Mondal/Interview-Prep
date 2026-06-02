# define main function
if __name__ == "__main__":
    # Define Constants For API Retry Logic
    max_retries = 5
    base_delay = 1
    backoff_multiplier = 2
    max_wait = 60
    attempt = 0
    response = None

    # Import Python Module:S1
    try:
        from pathlib import Path
        from dotenv import load_dotenv
        import os
        import sqlite3
        import time
        import string
        import mistune
        from jinja2 import Environment, FileSystemLoader
        from openai import AzureOpenAI
    except Exception as error:
        print(f'ERROR - [Main:S1] - {str(error)}')
        exit(1)

    # Define Folder Path:S2
    try:
        parent_folder_path = Path.cwd()
        input_folder_path = parent_folder_path / 'input'
        output_folder_path = parent_folder_path / 'output'
        database_folder_path = parent_folder_path / 'Database'
        env_file_path = parent_folder_path / '.env'
        system_prompt_file_path = input_folder_path / 'SystemPromptForQuestion.txt'
        question_file_path = input_folder_path / 'InterviewQuestions.txt'
        template_file_path = input_folder_path / 'AnswerTemplate.html'
        database_file_path = database_folder_path / 'interviewqa.db'
    except Exception as error:
        print(f'ERROR - [Main:S2] - {str(error)}')
        exit(1)

    # Load Environment Variables:S3
    try:
        if env_file_path.exists():
            load_dotenv(dotenv_path = env_file_path)

            # validate required environment variables
            required_credential = ['API_KEY', 'API_VERSION', 'API_ENDPOINT', 'CHAT_MODEL_NAME']
            missing_credential = [credential for credential in required_credential if not os.getenv(credential)]

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

    # Load Interview Questions From File:S4
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

    # Load System Prompt If Questions List Is Not Empty:S5
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

    # Create Database Connection And Cursor:S6
    try:
        # create global database connection and cursor
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
        print(f'SUCCESS - [Main:S6] - Database Connection And Cursor Created Successfully')
    except Exception as error:
        print(f'ERROR - [Main:S6] - {str(error)}')
        exit(1)

    # Create SQLite Database And Table:S7
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

    # Create And Test Azure OpenAI Client:S8
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
            # Call Azure OpenAI API For Answer:S9
            attempt = 0
            while attempt < max_retries:
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
                    # success, break the retry loop
                    break
                except Exception as error:
                    attempt += 1
                    if attempt < max_retries:
                        # calculate wait time with exponential backoff
                        wait_time = min(base_delay * (backoff_multiplier ** (attempt - 1)), max_wait)
                        print(f'WARNING - [Main:S9] - API Call Failed For Q{index} (Attempt {attempt}/{max_retries}): {str(error)}')
                        print(f'INFO - [Main:S9] - Retrying In {wait_time} Seconds...')
                        time.sleep(wait_time)
                    else:
                        print(f'ERROR - [Main:S9] - API Call Failed For Q{index} After {max_retries} Retries: {str(error)}')
                        database_connection.close()
                        exit(1)

            # Insert Into Database Using Global Connection:S10
            try:
                question_upper = question.upper().rstrip(string.punctuation) + '?'
                database_cursor.execute(
                    "INSERT INTO interview_qa_table (question_text, answer_text, input_token, output_token, model_name) VALUES (?, ?, ?, ?, ?)",
                    (question_upper, answer, prompt_tokens, completion_tokens, chat_model_name)
                )
                database_connection.commit()
                print(f'SUCCESS - [Main:S10] - Inserted "Q{index}" Into Database')
            except Exception as db_error:
                print(f'ERROR - [Main:S10] - Database Insert Failed For Q{index}: {str(db_error)}')
                database_connection.close()
                exit(1)

        # Close Database Connection After All Questions Processed:S11
        try:
            database_connection.close()
            print(f'SUCCESS - [Main:S11] - All Questions Processed And Database Connection Closed')
        except Exception as error:
            print(f'ERROR - [Main:S11] - {str(error)}')
    else:
        database_connection.close()
        exit(1)

    # Generate Single HTML File From Database Records With Markdown Rendering:S12
    try:
        database_connection = None

        # validate template file exists
        if not template_file_path.exists():
            print(f'ERROR - [Main:S12] - Template File Not Found: {template_file_path}')
            exit(1)

        # ensure output folder exists
        output_folder_path.mkdir(parents=True, exist_ok=True)

        # fetch all records from database
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
        database_cursor.execute("SELECT question_text, answer_text FROM interview_qa_table")
        records = database_cursor.fetchall()

        if records:
            print(f'INFO - [Main:S12] - Found {len(records)} Records To Export As HTML')

            # create markdown parser and render each answer
            markdown = mistune.create_markdown()
            qa_items = []
            for index, (question, answer) in enumerate(records, start = 1):
                qa_items.append({
                    'index': index,
                    'question': question,
                    'answer_html': markdown(answer)
                })

            # load jinja2 template from input folder and render
            env = Environment(loader=FileSystemLoader(str(input_folder_path)))
            template = env.get_template('AnswerTemplate.html')
            rendered_html = template.render(qa_items=qa_items)

            html_output_path = output_folder_path / 'Answer.html'
            with open(str(html_output_path), 'w', encoding='utf-8') as html_file:
                html_file.write(rendered_html)

            database_connection.close()
            print(f'SUCCESS - [Main:S12] - Answer.html Generated Successfully: {html_output_path}')
        else:
            print(f'INFO - [Main:S12] - No Records Found In Database To Export')
            database_connection.close()

    except Exception as error:
        print(f'ERROR - [Main:S12] - {str(error)}')
        if database_connection:
            database_connection.close()