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
        import os
        import sys
        from pathlib import Path
        from dotenv import load_dotenv
        import sqlite3
        import time
        import string
        import mistune
        from jinja2 import Environment, FileSystemLoader
        from openai import AzureOpenAI
    except Exception as error:
        print(f'ERROR - [Main:S1] - {str(error)}')
        exit(1)

    # Appending System Path:S2
    try:
        sys.path.append(Path.cwd())
    except Exception as error:
        print(f'ERROR - [Main:S2] - {str(error)}')
        exit(1)

    # Importing User-Define Module:S3
    try:
        from supportscripts.credentialcheck import credential_check
        from supportscripts.dbtablecreate import db_table_create
        from supportscripts.questionloadandcheck import question_load_and_check
    except Exception as error:
        print(f'ERROR - [Main:S3] - {str(error)}')
        exit(1)

    # Define Folder Path:S4
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
        print(f'ERROR - [Main:S4] - {str(error)}')
        exit(1)

    # Load And Validate Environment Variables Using credential_check Function:S5
    try:
        credential_result = credential_check(str(env_file_path))
        if credential_result['status'] != 'SUCCESS':
            print(f'ERROR - [Main:S5] - Credential Check Failed: {credential_result["message"]}')
            exit(1)
        
        # extract credentials from os.environ
        api_key = os.getenv('API_KEY')
        api_version = os.getenv('API_VERSION')
        api_endpoint = os.getenv('API_ENDPOINT')
        chat_model_name = os.getenv('CHAT_MODEL_NAME')
        print(f'SUCCESS - {credential_result["message"]}')
    except Exception as error:
        print(f'ERROR - [Main:S5] - {str(error)}')
        exit(1)

    # Create SQLite Database And Table Using "db_table_create" Function:S6
    try:
        table_create_result = db_table_create(str(database_file_path))
        if table_create_result['status'] != 'SUCCESS':
            print(f"ERROR - {table_create_result['required_file_name']}:{table_create_result['step']} - Database Table Creation Failed: {table_create_result['message']}")
            exit(1)
        print(f"SUCCESS - {table_create_result['message']}")
    except Exception as error:
        print(f'ERROR - [Main:S6] - {str(error)}')
        exit(1)

    # Load Questions From File And Insert Into Database Using "question_load_and_check" Function:S7
    try:
        question_load_and_check_result = question_load_and_check(str(question_file_path), str(database_file_path))
        if question_load_and_check_result['status'] != 'SUCCESS':
            print(f"ERROR - {question_load_and_check_result['file_name']}:{question_load_and_check_result['step']} - Question Load And Check Failed: {question_load_and_check_result['message']}")
            exit(1)
        print(f"SUCCESS - {question_load_and_check_result['message']}")
    except Exception as error:
        print(f'ERROR - [Main:S7] - {str(error)}')
        exit(1)

    # # Create And Test Azure OpenAI Client:S8
    # try:
    #     # initialize azure openai client with loaded environment variables
    #     client = AzureOpenAI(
    #         api_key = api_key,
    #         api_version = api_version,
    #         azure_endpoint = api_endpoint
    #     )

    #     # verify client object was created
    #     if client is None:
    #         print(f'ERROR - [Main:S8] - Failed To Create Azure OpenAI Client')
    #         database_connection.close()
    #         exit(1)

    #     # test the client with a simple api call
    #     test_response = client.chat.completions.create(
    #         model = chat_model_name,
    #         messages = [
    #             {"role": "system", "content": "You are a helpful assistant."},
    #             {"role": "user", "content": "Test connection. Reply with: SUCCESS"}
    #         ],
    #         temperature = 0.7,
    #         max_completion_tokens = 10
    #     )

    #     # verify test response and check for success keyword
    #     if test_response and test_response.choices and len(test_response.choices) > 0:
    #         response_content = test_response.choices[0].message.content

    #         # check if response contains "success"
    #         if response_content and ('success' in response_content.lower()):
    #             print(f'SUCCESS - Azure OpenAI Client Created And Tested Successfully')
    #         else:
    #             print(f'ERROR - [Main:S8] - API Validation Failed - Did Not Receive SUCCESS')
    #             print(f'  Received Response: {response_content}')
    #             database_connection.close()
    #             exit(1)
    #     else:
    #         print(f'ERROR - [Main:S8] - Client Test Call Failed - No Response')
    #         database_connection.close()
    #         exit(1)
    # except Exception as error:
    #     print(f'ERROR - [Main:S8] - {str(error)}')
    #     database_connection.close()
    #     exit(1)

    # # process questions with azure openai and store in database
    # if questions_list and question_answer_system_prompt:
    #     # loop through questions and process each one
    #     for index, question in enumerate(questions_list, start = 1):
    #         # Call Azure OpenAI API For Answer:S9
    #         attempt = 0
    #         while attempt < max_retries:
    #             try:
    #                 response = client.chat.completions.create(
    #                     model = chat_model_name,
    #                     messages = [
    #                         {"role": "system", "content": question_answer_system_prompt},
    #                         {"role": "user", "content": question}
    #                     ],
    #                     temperature = 0.7
    #                 )
    #                 # extract answer and token usage
    #                 answer = response.choices[0].message.content
    #                 prompt_tokens = response.usage.prompt_tokens
    #                 completion_tokens = response.usage.completion_tokens
    #                 # success, break the retry loop
    #                 break
    #             except Exception as error:
    #                 attempt += 1
    #                 if attempt < max_retries:
    #                     # calculate wait time with exponential backoff
    #                     wait_time = min(base_delay * (backoff_multiplier ** (attempt - 1)), max_wait)
    #                     print(f'WARNING - [Main:S10] - API Call Failed For Q{index} (Attempt {attempt}/{max_retries}): {str(error)}')
    #                     print(f'INFO - [Main:S10] - Retrying In {wait_time} Seconds...')
    #                     time.sleep(wait_time)
    #                 else:
    #                     print(f'ERROR - [Main:S10] - API Call Failed For Q{index} After {max_retries} Retries: {str(error)}')
    #                     database_connection.close()
    #                     exit(1)

    #         # Insert Into Database Using Global Connection:S11
    #         try:
    #             question_upper = question.upper().rstrip(string.punctuation) + '?'
    #             database_cursor.execute(
    #                 "INSERT INTO interview_qa_table (question_text, answer_text, input_token, output_token, model_name) VALUES (?, ?, ?, ?, ?)",
    #                 (question_upper, answer, prompt_tokens, completion_tokens, chat_model_name)
    #             )
    #             database_connection.commit()
    #             print(f'SUCCESS - Inserted "Q{index}" Into Database')
    #         except Exception as db_error:
    #             print(f'ERROR - [Main:S11] - Database Insert Failed For Q{index}: {str(db_error)}')
    #             database_connection.close()
    #             exit(1)

    # else:
    #     exit(1)

    # # Fetch All Records From Database:S12
    # try:
    #     database_cursor.execute("SELECT question_text, answer_text, input_token, output_token FROM interview_qa_table")
    #     records = database_cursor.fetchall()
    #     database_connection.close()
    #     print(f'SUCCESS - Fetched {len(records)} Records And Database Connection Closed')
    # except Exception as error:
    #     print(f'ERROR - [Main:S12] - {str(error)}')
    #     database_connection.close()
    #     exit(1)

    # # Generate Single HTML File From Database Records With Markdown Rendering:S13
    # try:
    #     if records:
    #         print(f'SUCCESS - Found {len(records)} Records To Export As HTML')

    #         # create markdown parser and render each answer
    #         markdown = mistune.create_markdown()
    #         qa_items = []
    #         for index, (question, answer, input_token, output_token) in enumerate(records, start = 1):
    #             qa_items.append({
    #                 'index': index,
    #                 'question': question,
    #                 'answer_html': markdown(answer),
    #                 'input_token': input_token,
    #                 'output_token': output_token
    #             })

    #         # load jinja2 template from input folder and render
    #         env = Environment(loader = FileSystemLoader(str(input_folder_path)))
    #         template = env.get_template('AnswerTemplate.html')
    #         rendered_html = template.render(qa_items = qa_items)

    #         html_output_path = output_folder_path / 'Answer.html'
    #         with open(str(html_output_path), 'w', encoding = 'utf-8') as html_file:
    #             html_file.write(rendered_html)

    #         print(f'SUCCESS - "Answer.html" Generated Successfully')
    #     else:
    #         print(f'INFO - No Records Found In Database To Export')
    # except Exception as error:
    #     print(f'ERROR - [Main:S13] - {str(error)}')
    #     exit(1)