# define "html_generator" function to fetch database records and generate HTML with markdown rendering
def html_generator(database_file_path: str, input_folder_path: str, output_folder_path: str) -> dict[str, str]:
    # Importing Python Modules: S1
    try:
        import sqlite3
        from pathlib import Path
        import mistune
        from jinja2 import Environment, FileSystemLoader
    except Exception as error:
        return {'status': 'ERROR', 'step': '1', 'file_name': 'HTML-Generator', 'message': str(error)}

    # Validate File Paths And Templates: S2
    try:
        # validate database file path exists
        database_file_path_obj = Path(database_file_path)
        if not database_file_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'HTML-Generator', 'message': f'Database File Not Found: {database_file_path}'}

        # validate input folder path exists
        input_folder_path_obj = Path(input_folder_path)
        if not input_folder_path_obj.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'HTML-Generator', 'message': f'Input Folder Not Found: {input_folder_path}'}

        # validate output folder path exists, if not create it
        output_folder_path_obj = Path(output_folder_path)
        if not output_folder_path_obj.exists():
            output_folder_path_obj.mkdir(parents = True, exist_ok = True)

        # validate template file exists
        template_file_path = input_folder_path_obj / 'AnswerTemplate.html'
        if not template_file_path.exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'HTML-Generator', 'message': f'Template File Not Found: {template_file_path}'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '2', 'file_name': 'HTML-Generator', 'message': str(error)}

    # Create Database Connection: S3
    try:
        # create database connection and cursor
        database_connection = sqlite3.connect(str(database_file_path))
        database_cursor = database_connection.cursor()
    except Exception as error:
        return {'status': 'ERROR', 'step': '3', 'file_name': 'HTML-Generator', 'message': str(error)}

    # Fetch All Records From Database: S4
    try:
        # fetch all records with processed answers (row_status = 3)
        fetch_query = """
        SELECT final_question_text, answer_text, input_token, output_token FROM interview_qa_table
        WHERE row_status = 3
        ORDER BY id ASC
        """
        database_cursor.execute(fetch_query)
        records = database_cursor.fetchall()
        database_connection.close()

        if not records:
            return {'status': 'INFO', 'step': '4', 'file_name': 'HTML-Generator', 'message': 'No Records Found In Database To Export'}
    except Exception as error:
        database_connection.close()
        return {'status': 'ERROR', 'step': '4', 'file_name': 'HTML-Generator', 'message': str(error)}

    # Generate HTML From Database Records With Markdown Rendering: S5
    try:
        # create markdown parser
        markdown = mistune.create_markdown()

        # prepare qa items for template rendering
        qa_items = []
        for index, (question, answer, input_token, output_token) in enumerate(records, start = 1):
            qa_items.append({
                'index': index,
                'question': question,
                'answer_html': markdown(answer),
                'input_token': input_token,
                'output_token': output_token
            })

        # load jinja2 template from input folder and render
        env = Environment(loader = FileSystemLoader(str(input_folder_path_obj)))
        template = env.get_template('AnswerTemplate.html')
        rendered_html = template.render(qa_items = qa_items)

        # write rendered html to output file
        html_output_path = output_folder_path_obj / 'Answer.html'
        with open(str(html_output_path), 'w', encoding = 'utf-8') as html_file:
            html_file.write(rendered_html)

        return {'status': 'SUCCESS', 'step': '5', 'file_name': 'HTML-Generator', 'message': f'All {len(records)} Questions Answer Exported Into "output/Answer.html" File'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '5', 'file_name': 'HTML-Generator', 'message': str(error)}