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
        from supportscripts.questionload import question_load
        from supportscripts.questionprocess import question_process
        from supportscripts.questionanswerprocess import question_answer_process
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
        system_prompt_file_path_for_correct_question = input_folder_path / 'CorrectQuestionGenerationSystemPrompt.txt'
        system_prompt_file_path_for_question_answer = input_folder_path / 'QuestionAnswerSystemPrompt.txt'
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

    # Load Questions From File And Insert Into Database Using "question_load" Function:S7
    try:
        question_load_result = question_load(str(question_file_path), str(database_file_path))
        if question_load_result.get('status') != 'SUCCESS':
            error_msg = question_load_result.get('message', 'Unknown error')
            print(f"ERROR - [Main:S7] - Question Load Failed: {error_msg}")
            exit(1)
        print(f"SUCCESS - {question_load_result['message']}")
    except Exception as error:
        print(f'ERROR - [Main:S7] - {str(error)}')
        exit(1)

    # Process Questions With Azure OpenAI Using "question_process" Function:S8
    try:
        question_process_result = question_process(str(database_file_path), str(system_prompt_file_path_for_correct_question))
        if question_process_result.get('status') != 'SUCCESS':
            error_msg = question_process_result.get('message', 'Unknown error')
            print(f"ERROR - [Main:S8] - Question Process Failed: {error_msg}")
            exit(1)
        print(f"SUCCESS - {question_process_result['message']}")
    except Exception as error:
        print(f'ERROR - [Main:S8] - {str(error)}')
        exit(1)

    # Process Question Answers With Azure OpenAI Using "question_answer_process" Function:S9
    try:
        question_answer_process_result = question_answer_process(str(database_file_path), str(system_prompt_file_path_for_question_answer))
        if question_answer_process_result.get('status') != 'SUCCESS':
            error_msg = question_answer_process_result.get('message', 'Unknown error')
            print(f"ERROR - [Main:S9] - Question Answer Process Failed: {error_msg}")
            exit(1)
        print(f"SUCCESS - {question_answer_process_result['message']}")
    except Exception as error:
        print(f'ERROR - [Main:S9] - {str(error)}')
        exit(1)

    # # Fetch All Records From Database:S13
    # try:
    #     database_cursor.execute("SELECT question_text, answer_text, input_token, output_token FROM interview_qa_table")
    #     records = database_cursor.fetchall()
    #     database_connection.close()
    #     print(f'SUCCESS - Fetched {len(records)} Records And Database Connection Closed')
    # except Exception as error:
    #     print(f'ERROR - [Main:S13] - {str(error)}')
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