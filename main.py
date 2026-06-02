# Define Main Function
if __name__ == "__main__":
    # Importing Python Module:S1
    try:
        from pathlib import Path
    except Exception as error:
        print(f'ERROR - [Main:S1] - {str(error)}')

    # Define Folder Path:S2
    try:
        parent_folder_path = Path.cwd()
        input_folder_path = parent_folder_path / 'input'
        output_folder_path = parent_folder_path / 'output'
        system_prompt_file_path = input_folder_path / 'SystemPromptForQuestion.txt'
        question_file_path = input_folder_path / 'InterviewQuestions.txt'
    except Exception as error:
        print(f'ERROR - [Main:S2] - {str(error)}')

    # Load Interview Questions From File:S3
    try:
        if question_file_path.exists():
            with open(question_file_path, 'r', encoding = 'utf-8') as question_file:
                questions_list = [line.strip() for line in question_file.readlines() if line.strip()]
        else:
            print(f'ERROR - [Main:S3] - File Not Found: {question_file_path}')
            questions_list = []
    except Exception as error:
        print(f'ERROR - [Main:S3] - {str(error)}')