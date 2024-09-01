import os
import requests
import pandas as pd
from keep_alive import keep_alive

keep_alive()

COMMANDS_KEY = os.environ['COMMANDS_KEY']
STATS_KEY = os.environ['STATS_KEY']
API_KEY = os.environ['API_KEY']

# Importa planilha do Google Sheets com comandos e respostas
commands = ('https://docs.google.com/spreadsheets/d/' + COMMANDS_KEY +
            '/export?gid=0&format=csv')

# Lê a planilha CSV diretamente da URL
df = pd.read_csv(commands)
# Mostra as primeiras linhas do DataFrame (0 linhas para conferir o cabeçalho)
df.head(0)

# Lê estatísticas do Dendê Tool
stats_url = ('https://docs.google.com/spreadsheets/d/' + STATS_KEY +
             '/export?gid=1076143484&format=csv')
# Lê a planilha CSV diretamente da URL
stats = pd.read_csv(stats_url)
# Extrai e limpa o texto da célula específica
apl_total = stats.iloc[1, 5]
apl_igv = stats.iloc[1, 6]
apl_ogv = stats.iloc[1, 9]
apl_ogta = stats.iloc[1, 10]
apl_ogte = stats.iloc[1, 11]


# Define a URL base para a API do Telegram
base_url = ('https://api.telegram.org/bot' + API_KEY)


# Função para ler mensagens recebidas
def read_msg(offset):
    # Parâmetros para buscar atualizações a partir do último offset
    parameters = {"offset": offset}
    # Faz uma requisição GET para obter atualizações do bot
    resp = requests.get(base_url + "/getUpdates", data=parameters)
    data = resp.json()
    print(data)  # Imprime a resposta da API para debug

    # Processa cada resultado e envia uma resposta
    for result in data["result"]:
        send_msg(result)

    # Atualiza o offset para a próxima requisição
    if data["result"]:
        return data["result"][-1]["update_id"] + 1


# Função para gerar uma resposta automática com base na mensagem recebida
def auto_answer(message):
    
    # Verifica se a mensagem é um comando
    if not message.startswith('/'):
        return None  # Ignora a mensagem se não começar com "/"

    # Separa o comando do @ do usuário
    if '@' in message:
        message = message.split('@')[0]
    # Procura a resposta correspondente à pergunta recebida
    answer = df.loc[df['Question'].str.lower() == message.lower()]

    if not answer.empty:
        answer = answer.iloc[0]['Answer']
        # Substitui o placeholder pelo texto da célula específica, se necessário
        answer = answer.replace('{apl_total}', apl_total)
        answer = answer.replace('{apl_igv}', apl_igv)
        answer = answer.replace('{apl_ogv}', apl_ogv)
        answer = answer.replace('{apl_ogta}', apl_ogta)
        answer = answer.replace('{apl_ogte}', apl_ogte)
        return answer
    else:
        return "Não sei esse comando não pvt, manda Ananda me programar melhor aê"


# Função para enviar uma mensagem de volta ao chat no Telegram
def send_msg(message):
    try:
        if "message" in message:
            msg = message["message"]
            if "text" in msg:
                text = msg["text"]
                message_id = msg["message_id"]
                chat_id = msg["chat"]["id"]  # Pega o chat_id do chat recebido
                # Gera a resposta automática
                answer = auto_answer(text)

                # Parâmetros para enviar a resposta
                parameters = {
                    "chat_id": chat_id,
                    "text": answer,
                    "reply_to_message_id": message_id
                }
                # Faz uma requisição GET para enviar a mensagem
                resp = requests.get(base_url + "/sendMessage",
                                    params=parameters)
                resp.raise_for_status(
                )  # Levanta uma exceção para status de erro HTTP
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


# Offset inicial para começar a ler as mensagens
offset = 0

# Loop infinito para ler mensagens continuamente
while True:
    offset = read_msg(offset)
