# define "credential_check" function to check if the provided environment credentials are valid
def credential_check(env_file_path: str) -> dict[str, str]:
    # Importing Python Modules:S1
    try:
        import os
        from dotenv import load_dotenv
        from pathlib import Path
    except Exception as error:
        return {'status': 'ERROR', 'step': '1', 'file_name': 'Credential-Check', 'message': str(error)}

    # Load And Validate Environment Variables:S2
    try:
        # validate if env file exists
        if not Path(env_file_path).exists():
            return {'status': 'ERROR', 'step': '2', 'file_name': 'Credential-Check', 'message': f'".env" File Not Found: {env_file_path}'}
        
        # load environment variables from .env file
        load_dotenv(dotenv_path = env_file_path)
    except Exception as error:
        return {'status': 'ERROR', 'step': '2', 'file_name': 'Credential-Check', 'message': str(error)}

    # Validate Required Credentials:S3
    try:
        # define required credentials
        required_credential = ['API_KEY', 'API_VERSION', 'API_ENDPOINT', 'CHAT_MODEL_NAME']
        missing_credential = [credential for credential in required_credential if not os.getenv(credential)]

        # check if any required credentials are missing
        if missing_credential:
            return {'status': 'ERROR', 'step': '3', 'file_name': 'Credential-Check', 'message': f'Missing Environment Variables: {", ".join(missing_credential)}'}

        # set credentials into os environment level
        os.environ['API_KEY'] = os.getenv('API_KEY')
        os.environ['API_VERSION'] = os.getenv('API_VERSION')
        os.environ['API_ENDPOINT'] = os.getenv('API_ENDPOINT')
        os.environ['CHAT_MODEL_NAME'] = os.getenv('CHAT_MODEL_NAME')

        # return success status
        return {'status': 'SUCCESS', 'step': '3', 'file_name': 'Credential-Check', 'message': 'Environment Variables Loaded And Set Successfully'}
    except Exception as error:
        return {'status': 'ERROR', 'step': '3', 'file_name': 'Credential-Check', 'message': str(error)}