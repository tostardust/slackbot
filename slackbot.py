import subprocess
import threading
import logging
import uuid
import texts
import config
import os
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/slack/command/help', methods=['POST'])
def help_command():
    channel_id = request.form['channel_id']
    client = WebClient(token=config.BOT_TOKEN)
    try:
        client.chat_postMessage(channel=channel_id, text=texts.help)
    except SlackApiError as e:
        logging.error(f"Slack API Error: {e}")
    return '', 200
    
@app.route('/slack/command/test', methods=['POST'])
def handle_command():

    user_id = request.form.get('user_id')
    users = [config.USER_ID_1, config.USER_ID_2]
    if user_id not in users:
        return jsonify({'text': texts.not_authorized})
    
    text = request.form.get('text').strip().split()
    command = text[0] if len(text) > 0 else None
    sub_command = text[1] if len(text) > 1 else None
    response_url = request.form.get('response_url')

    unique_id = str(uuid.uuid4())
    report_file_name = f"report_{unique_id}.html"
    report_file_path = f"reports/transactions/{report_file_name}"

    newman_command = construct_newman_command(command, sub_command, report_file_path)
    response_message = create_response_message(command, sub_command)
    channel_id = request.form['channel_id']
    client = WebClient(token=config.BOT_TOKEN)

    if newman_command:
        threading.Thread(target=run_newman_and_respond, args=(response_url, newman_command, report_file_path)).start()
        client.chat_postMessage(channel=channel_id, text=response_message)
        return '', 200
    else:
        return jsonify({'text': texts.help})

def create_response_message(command, sub_command):
    if command == 'all':
        if sub_command and sub_command.startswith('stream-'):
            return texts.all_tests_specific_env + f"{sub_command}..."
        else:
            return texts.all_tests_default_env
    elif command in ['kzt', 'ved']:
        uppercase = command.upper()
        if sub_command and sub_command.startswith('stream-'):
            return f"{texts.specific_folder_specific_env}{sub_command} " + f"для команды {uppercase}..."
        else:
            return f"{texts.specific_folder_default_env}{uppercase}..."
    else:
        return texts.general_error

def construct_newman_command(command, sub_command, report_file_path):

    base_command = f'newman run test.json --ssl-client-cert cert.pem --ssl-client-key cert.pem --ssl-client-passphrase {config.CERT_PASSWORD} --insecure -r htmlextra'

    if command == 'all':
        if sub_command and sub_command.startswith('stream-'):
            environment_number = sub_command.split('-')[1]
            return f'{base_command} --env-var environment=stream-{environment_number} --reporter-htmlextra-export "{report_file_path}"'
        else:
            return f'{base_command} --reporter-htmlextra-export "{report_file_path}"'

    elif command in ['kzt', 'ved']:
        folder_command = f'{base_command} --folder {command}'
        if sub_command and sub_command.startswith('stream-'):
            environment_number = sub_command.split('-')[1]
            return f'{folder_command} --env-var environment=stream-{environment_number} --reporter-htmlextra-export "{report_file_path}"'
        else:
            return f'{folder_command} --reporter-htmlextra-export "{report_file_path}"'

    else:
        return None

def run_newman_and_respond(response_url, newman_command, report_file_path):
    try:
        process = subprocess.Popen(newman_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        logging.info(f"Newman process completed. Report path: {report_file_path}")
        timestamp = datetime.now().strftime("%d.%m.%Y, %H:%M")
        if os.path.exists(report_file_path):
            client = WebClient(token=config.BOT_TOKEN)
            if process.returncode == 0:
                response = client.files_upload_v2(channel=config.CHANNEL_ID,
                                            file=report_file_path,
                                            title=f'Отчет от {timestamp}',
                                            initial_comment=texts.success_run)
                assert response['ok']
            elif process.returncode != 0:
                response = client.files_upload_v2(channel=config.CHANNEL_ID,
                                            file=report_file_path,
                                            title=f'Отчет от {timestamp}',
                                            initial_comment=texts.failed_test)
                assert response['ok']
        else:
            logging.error(f"Report file not found: {report_file_path}")
    except Exception as e:
        logging.exception("An error occurred while executing Newman")

if __name__ == '__main__':
    app.run(debug=True, port=3000)