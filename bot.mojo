import requests
import pandas as pd

# Importa planilha do Google Sheets com comandos e respostas
commands = ('https://docs.google.com/spreadsheets/d/' +
                   '15-6Hgfd_pxuRLYHJGMIFLx4bjJl4k-iiCDkEYecea-c' +
                   '/export?gid=0&format=csv')

# Lê a planilha CSV diretamente da URL
df = pd.read_csv(commands)
# Mostra as primeiras linhas do DataFrame (0 linhas para conferir o cabeçalho)
df.head(0)


# Lê estatísticas do Dendê Tool
stats_url = ('https://docs.google.com/spreadsheets/d/' +
                   '1Im-0MojG7UlW3W4PzHExYI96IU79FXs52MU_MHZ9OMM' +
                   '/export?gid=1076143484&format=csv')

# Lê a planilha CSV diretamente da URL
stats = pd.read_csv(stats_url)
# Extrai e limpa o texto da célula específica
apl_total = stats.iloc[1, 5]
apl_total = str(apl_total).strip()

apl_igv = stats.iloc[1, 6]
apl_igv = str(apl_igv).strip()

apl_ogv = stats.iloc[1, 9]
apl_ogv = str(apl_ogv).strip()

apl_ogta = stats.iloc[1, 10]
apl_ogta = str(apl_ogta).strip()

apl_ogte = stats.iloc[1, 11]
apl_ogte = str(apl_ogte).strip()

# Define a URL base para a API do Telegram
base_url = "https://api.telegram.org/bot7501122668:AAHER_PYTh6QNbIXsa3ig9Kh1SyB1iNRJtk"

# Função para ler mensagens recebidas
def read_msg(offset):
    # Parâmetros para buscar atualizações a partir do último offset
    parameters = {
        "offset" : offset
    }
    # Faz uma requisição GET para obter atualizações do bot
    resp = requests.get(base_url + "/getUpdates", data = parameters)
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
                # Gera a resposta automática
                answer = auto_answer(text)

                # Parâmetros para enviar a resposta
                parameters = {
                    # "chat_id": "-4598989403",
                    "text": answer,
                    "reply_to_message_id": message_id
                }
                # Faz uma requisição GET para enviar a mensagem
                resp = requests.get(base_url + "/sendMessage", params=parameters)
                resp.raise_for_status()  # Levanta uma exceção para status de erro HTTP
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
