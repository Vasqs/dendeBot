import io
import os

import pandas as pd
import requests
from dotenv import load_dotenv

from keep_alive import keep_alive

load_dotenv()

# Mantém o bot ativo na web
keep_alive()

# Obtém chaves de ambiente para acessar as planilhas e a API do Telegram
COMMANDS_KEY = os.environ["COMMANDS_KEY"]
STATS_KEY = os.environ["STATS_KEY"]
API_KEY = os.environ["API_KEY"]


# URLs para acessar as planilhas do Google Sheets em formato CSV
commands_url = (
    f"https://docs.google.com/spreadsheets/d/{COMMANDS_KEY}/export?gid=0&format=csv"
)
stats_url_template = (
    f"https://docs.google.com/spreadsheets/d/{STATS_KEY}/export?gid={{gid}}&format=csv"
)

# URL base para interagir com a API do Telegram
base_url = f"https://api.telegram.org/bot{API_KEY}"


def fetch_csv(url):
    # Faz o download do arquivo CSV da URL fornecida
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # Garante que a solicitação foi bem-sucedida
    # Lê o conteúdo CSV em um DataFrame do pandas
    return pd.read_csv(io.StringIO(response.content.decode("utf-8")))


def fetch_commands():
    # Obtém o DataFrame contendo os comandos
    return fetch_csv(commands_url)


def format_currency(value):
    if value is None:
        return "0"

    # Remove o prefixo "R$ " e espaços
    value = value.replace("R$ ", "").replace(".", "").replace(",", ".")

    try:
        number = float(value)
    except ValueError:
        return value  # Retorna o valor original se não puder converter para float

    # Formata o número
    if number >= 1_000:
        return f"{number / 1_000:.0f}k"
    else:
        return str(int(number))


def fetch_stats(gid, type_):
    # Obtém o DataFrame contendo as estatísticas da página especificada
    stats_url = stats_url_template.format(gid=gid)
    stats = fetch_csv(stats_url)

    if type_ == "APL":
        return {
            "total": stats.iloc[1, 5],
            "igv": stats.iloc[1, 6],
            "ogv": stats.iloc[1, 9],
            "ogta": stats.iloc[1, 10],
            "ogte": stats.iloc[1, 11],
        }
    elif type_ == "APD":
        return {"plan": stats.iloc[3, 14], "done": stats.iloc[3, 15]}
    elif type_ == "OPEN":
        return {"plan": stats.iloc[11, 2], "done": stats.iloc[11, 3]}
    elif type_ == "FIN_PLAN":
        return {"plan": format_currency(stats.iloc[9, 5])}
    elif type_ == "FIN_DONE":
        return {"done": format_currency(stats.iloc[9, 5])}
    else:
        raise ValueError("Invalid type specified. Use 'APL' or 'APD'.")


# Obtém os dados iniciais das planilhas
df_commands = fetch_commands()
stats_apl = fetch_stats(1076143484, "APL")
stats_apd = fetch_stats(1226391324, "APD")
stats_open = fetch_stats(1226391324, "OPEN")
stats_fin_plan = fetch_stats(1529433403, "FIN_PLAN")
stats_fin_done = fetch_stats(1529433403, "FIN_DONE")

# Combine os dados das duas páginas conforme necessário
combined_stats = {
    "apl_total": stats_apl["total"],
    "apl_igv": stats_apl["igv"],
    "apl_ogv": stats_apl["ogv"],
    "apl_ogta": stats_apl["ogta"],
    "apl_ogte": stats_apl["ogte"],
    "apd_plan": stats_apd["plan"],
    "apd_done": stats_apd["done"],
    "open_plan": stats_open["plan"],
    "open_done": stats_open["done"],
    "fin_plan": stats_fin_plan["plan"],
    "fin_done": stats_fin_done["done"],
}


def replace_placeholders(answer, stats):
    # Substitui os placeholders pelos valores correspondentes
    for key, value in stats.items():
        answer = answer.replace(f"{{{key}}}", str(value))
    return answer


def change_title(current_title):
    # Função para verificar o valor da célula específica e mudar o título do grupo se necessário
    df_commands = fetch_commands()
    new_title = df_commands.iloc[0, 2]

    # Verifica se o valor não é NaN e se é uma string válida
    if pd.notna(new_title) and isinstance(new_title, str) and new_title.strip():
        # Substitui placeholders no novo título
        new_title = replace_placeholders(new_title, combined_stats)

        if new_title != current_title:
            # Atualiza o título do grupo via API do Telegram
            parameters = {"chat_id": "-1002189305283", "title": new_title}
            resp = requests.get(
                f"{base_url}/setChatTitle", params=parameters, timeout=10
            )
            resp.raise_for_status()
            print(f"Título do grupo alterado para: {new_title}")
            return new_title
    else:
        print("Valor inválido para o título do grupo, mantendo o título atual.")

    return current_title


current_title = df_commands.iloc[2, 1]


def read_msg(offset):
    # Lê mensagens da API do Telegram a partir do offset fornecido
    parameters = {"offset": offset}
    resp = requests.get(f"{base_url}/getUpdates", params=parameters, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # Envia cada mensagem recebida
    for result in data["result"]:
        send_msg(result)

    # Atualiza o offset para evitar processar mensagens duplicadas
    return data["result"][-1]["update_id"] + 1 if data["result"] else offset


def auto_answer(message):
    # Gera uma resposta automática para a mensagem recebida
    if not message.startswith("/"):
        return None

    # Remove o nome de usuário se presente
    message = message.split("@")[0] if "@" in message else message

    # Busca pela resposta correspondente ao comando
    answer_row = df_commands.loc[
        df_commands["Question"].str.lower() == message.lower(),
    ]

    if not answer_row.empty:
        answer = answer_row.iloc[0]["Answer"]
        return replace_placeholders(answer, combined_stats)
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
                    # Garante o encoding correto
                    "text": answer.encode("utf-8").decode("utf-8"),
                    "reply_to_message_id": message_id,
                }
                resp = requests.get(
                    f"{base_url}/sendMessage", params=parameters, timeout=10
                )
                resp.raise_for_status()
                print("Message received")
            else:
                print("Mensagem with no text:", msg)
        else:
            print("Mensagem not found:", message)
    except requests.exceptions.Timeout:
        print("Timeout error occurred")
    except requests.exceptions.ConnectionError:
        print("Connection error occurred")
    except requests.exceptions.HTTPError as http_err:
        if resp.status_code == 400:
            print("Erro 400: Ignoring deleted message")
        else:
            print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    except Exception as err:
        print(f"An unexpected error occurred: {err}")


# Loop principal para ler mensagens continuamente
offset = 0
while True:
    offset = read_msg(offset)
    current_title = change_title(current_title)
