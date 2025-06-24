import redis
from flask import Flask, render_template, request, jsonify
import uuid
import threading
import time

app = Flask(__name__)

# Substitua pelo IP real do seu dispositivo Android executando o Redis
REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# Instância do cliente Redis para comunicação (publish)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# Armazena o ID do cliente, o canal ativo e um flag para controle dos botões
# ALTERADO: Adicionado 'awaiting_quote_response'
client_data = {} # {session_id: {'client_id': '...', 'active_channel': '...', 'messages': [], 'awaiting_quote_response': False}}

@app.route('/')
def client_index():
    session_id = str(uuid.uuid4())
    client_id = f"cliente_{uuid.uuid4().hex[:8]}"
    # ALTERADO: Inicializa 'awaiting_quote_response'
    client_data[session_id] = {'client_id': client_id, 'active_channel': None, 'messages': [], 'awaiting_quote_response': False}
    return render_template('client.html', client_id=client_id, session_id=session_id)

@app.route('/solicit_maintenance', methods=['POST'])
def solicit_maintenance():
    session_id = request.form['session_id']
    problem_description = request.form['problem_description']
    
    if session_id not in client_data:
        return jsonify({"status": "error", "message": "Sessão inválida."}), 400

    client_id = client_data[session_id]['client_id']
    initial_channel = "initial_maintenance_requests"
    message = f"SOLICITAR_MANUTENCAO|{client_id}|{problem_description}"
    
    r.publish(initial_channel, message)
    
    client_data[session_id]['active_channel'] = f"maintenance_channel_{client_id}"
    client_data[session_id]['messages'].append(f"Você solicitou manutenção: '{problem_description}'")
    client_data[session_id]['messages'].append(f"Aguardando orçamento ou notificação do técnico...")
    client_data[session_id]['messages'].append(f"Ouvindo atualizações no canal: {client_data[session_id]['active_channel']}")

    # Inicia a escuta em uma thread separada para não bloquear a requisição web
    threading.Thread(target=listen_for_client_messages, args=(session_id, client_data[session_id]['active_channel'])).start()

    return jsonify({"status": "success", "message": "Solicitação enviada. Aguardando notificações..."})

@app.route('/send_response', methods=['POST'])
def send_response():
    session_id = request.form['session_id']
    response_type = request.form['response_type'] # 'aprovar' ou 'negar'
    
    if session_id not in client_data or not client_data[session_id]['active_channel']:
        return jsonify({"status": "error", "message": "Nenhum canal ativo para resposta."}), 400

    client_id = client_data[session_id]['client_id']
    active_channel = client_data[session_id]['active_channel']

    if response_type == 'aprovar':
        r.publish(active_channel, f"APROVAR_ORCAMENTO|{client_id}|Orçamento aprovado.")
        client_data[session_id]['messages'].append("Aprovação enviada ao técnico.")
    else:
        r.publish(active_channel, f"NEGAR_ORCAMENTO|{client_id}|Orçamento negado.")
        client_data[session_id]['messages'].append("Recusa enviada ao técnico.")
    
    # ALTERADO: Após enviar a resposta, desativa o flag para esconder os botões
    client_data[session_id]['awaiting_quote_response'] = False

    return jsonify({"status": "success", "message": "Resposta enviada."})

@app.route('/get_messages/<session_id>')
def get_messages(session_id):
    if session_id in client_data:
        messages = client_data[session_id]['messages']
        # ALTERADO: Pega o estado do flag para enviar ao frontend
        awaiting_response = client_data[session_id]['awaiting_quote_response']
        client_data[session_id]['messages'] = [] # Limpa as mensagens após enviá-las
        # ALTERADO: Retorna o flag 'awaiting_response'
        return jsonify({"messages": messages, "awaiting_response": awaiting_response})
    return jsonify({"messages": [], "awaiting_response": False})


def listen_for_client_messages(session_id, channel_name):
    pubsub = r.pubsub()
    pubsub.subscribe(channel_name)
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            data = message['data'] # REMOVIDO .decode()
            
            if session_id not in client_data: # Sessão pode ter sido encerrada
                pubsub.unsubscribe(channel_name)
                break

            client_data[session_id]['messages'].append(f"Recebido: {data}")

            # ALTERADO: Extrai o valor do orçamento da mensagem NOTIFICACAO_ORCAMENTO
            if data.startswith("NOTIFICACAO_ORCAMENTO"):
                parts = data.split('|')
                if len(parts) > 2: # Espera "NOTIFICACAO_ORCAMENTO|client_id|quote_amount"
                    quote_amount = parts[2]
                    client_data[session_id]['messages'].append(f"Notificação de orçamento recebida: R$ {quote_amount}. Aprovar ou recusar?")
                else: # Fallback para o caso de a mensagem não ter o valor (versões antigas)
                    client_data[session_id]['messages'].append("Notificação de orçamento recebida. Aprovar ou recusar?")
                # ALTERADO: Ativa o flag para mostrar os botões de aprovação/recusa
                client_data[session_id]['awaiting_quote_response'] = True

            elif "NOTIFICACAO_CONCLUSAO" in data:
                client_data[session_id]['messages'].append("Serviço concluído! Obrigado!")
                pubsub.unsubscribe(channel_name)
                client_data[session_id]['active_channel'] = None
                # ALTERADO: Desativa o flag ao concluir
                client_data[session_id]['awaiting_quote_response'] = False
                break
            elif "SERVICO_CANCELADO" in data:
                client_data[session_id]['messages'].append("Serviço foi cancelado.")
                pubsub.unsubscribe(channel_name)
                client_data[session_id]['active_channel'] = None
                # ALTERADO: Desativa o flag ao cancelar
                client_data[session_id]['awaiting_quote_response'] = False
                break
            elif "CHANNEL_CLOSED" in data:
                client_data[session_id]['messages'].append(f"Canal {channel_name} explicitamente fechado pelo sistema.")
                pubsub.unsubscribe(channel_name)
                client_data[session_id]['active_channel'] = None
                # ALTERADO: Desativa o flag ao fechar o canal
                client_data[session_id]['awaiting_quote_response'] = False
                break
        time.sleep(0.1)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)