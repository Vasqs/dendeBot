import os
import requests
import pandas as pd
import io
from keep_alive import keep_alive

# Mantém o bot ativo na web
keep_alive()

# Obtém chaves de ambiente para acessar as planilhas e a API do Telegram
COMMANDS_KEY = os.environ['COMMANDS_KEY']
STATS_KEY = os.environ['STATS_KEY']
API_KEY = os.environ['API_KEY']

# URLs para acessar as planilhas do Google Sheets em formato CSV
commands_url = f'https://docs.google.com/spreadsheets/d/{COMMANDS_KEY}/export?gid=0&format=csv'
stats_url = f'https://docs.google.com/spreadsheets/d/{STATS_KEY}/export?gid=1076143484&format=csv'

def fetch_csv(url):
    # Faz o download do arquivo CSV da URL fornecida
    response = requests.get(url)
    response.raise_for_status()  # Garante que a solicitação foi bem-sucedida
    return pd.read_csv(io.StringIO(response.content.decode('utf-8')))  # Lê o conteúdo CSV em um DataFrame do pandas

def fetch_commands():
    # Obtém o DataFrame contendo os comandos
    return fetch_csv(commands_url)

def fetch_stats():
    # Obtém o DataFrame contendo as estatísticas e retorna um dicionário com valores específicos
    stats = fetch_csv(stats_url)
    return {
        'apl_total': stats.iloc[1, 5],
        'apl_igv': stats.iloc[1, 6],
        'apl_ogv': stats.iloc[1, 9],
        'apl_ogta': stats.iloc[1, 10],
        'apl_ogte': stats.iloc[1, 11]
    }

# Obtém os dados iniciais das planilhas
df_commands = fetch_commands()
stats = fetch_stats()

# URL base para interagir com a API do Telegram
base_url = f'https://api.telegram.org/bot{API_KEY}'

def read_msg(offset):
    # Lê mensagens da API do Telegram a partir do offset fornecido
    parameters = {"offset": offset}
    resp = requests.get(f'{base_url}/getUpdates', params=parameters)
    resp.raise_for_status()
    data = resp.json()

    # Envia cada mensagem recebida
    for result in data["result"]:
        send_msg(result)

    # Atualiza o offset para evitar processar mensagens duplicadas
    return data["result"][-1]["update_id"] + 1 if data["result"] else offset

def auto_answer(message):
    # Gera uma resposta automática para a mensagem recebida
    if not message.startswith('/'):
        return None

    # Remove o nome de usuário se presente
    message = message.split('@')[0] if '@' in message else message

    # Busca pela resposta correspondente ao comando
    answer_row = df_commands.loc[df_commands['Question'].str.lower() == message.lower()]

    if not answer_row.empty:
        answer = answer_row.iloc[0]['Answer']
        for key, value in stats.items():
            answer = answer.replace(f'{{{key}}}', value)
        return answer
    else:
        return "Não sei esse comando não pvt, manda Ananda me programar melhor aê"

def send_msg(message):
    # Envia uma mensagem de volta ao usuário no Telegram
    try:
        if "message" in message:
            msg = message["message"]
            if "text" in msg:
                text = msg["text"]
                message_id = msg["message_id"]
                chat_id = msg["chat"]["id"]
                answer = auto_answer(text)  # Obtém a resposta automática

                parameters = {
                    "chat_id": chat_id,
                    "text": answer.encode('utf-8').decode('utf-8'),  # Garante o encoding correto
                    "reply_to_message_id": message_id
                }
                resp = requests.get(f'{base_url}/sendMessage', params=parameters)
                resp.raise_for_status()
                print(resp.text)
            else:
                print("Mensagem sem texto:", msg)
        else:
            print("Mensagem não encontrada:", message)
    except requests.exceptions.HTTPError as http_err:
        if resp.status_code == 400:
            print("Erro 400: Ignorando mensagem excluída")
        else:
            print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")

# Loop principal para ler mensagens continuamente
offset = 0
while True:
    offset = read_msg(offset)
