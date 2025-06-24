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

# Armazena ordens de serviço ativas para o técnico
# {client_id: {'problem': '...', 'channel': '...', 'status': '...', 'messages': [], 'quote': None}}
active_service_orders = {}

# Para gerenciar o pubsub do técnico em uma thread separada
technician_pubsub = r.pubsub()
technician_id = f"tecnico_{uuid.uuid4().hex[:8]}" # ID do técnico global para esta instância do Flask

@app.route('/')
def technician_index():
    return render_template('technician.html', technician_id=technician_id)

@app.route('/get_active_orders')
def get_active_orders():
    # Retorna uma cópia para evitar problemas de modificação durante iteração
    return jsonify({"orders": active_service_orders})

@app.route('/emit_quote', methods=['POST'])
def emit_quote():
    client_id = request.form['client_id']
    quote_amount = request.form['quote_amount']

    if client_id not in active_service_orders:
        return jsonify({"status": "error", "message": "Ordem de serviço não encontrada."}), 404

    service_channel = active_service_orders[client_id]['channel']
    quote_message = f"MENSAGEM_ORCAMENTO|{client_id}|{quote_amount}"
    r.publish(service_channel, quote_message)
    
    active_service_orders[client_id]['status'] = 'quote sent'
    # >>> ALTERADO AQUI: Armazenar o valor do orçamento no dicionário da OS <<<
    active_service_orders[client_id]['quote'] = quote_amount 
    active_service_orders[client_id]['messages'].append(f"Você emitiu orçamento para {client_id}: {quote_amount}. Aguardando aprovação.")
    return jsonify({"status": "success", "message": "Orçamento enviado."})

@app.route('/execute_service', methods=['POST'])
def execute_service():
    client_id = request.form['client_id']

    if client_id not in active_service_orders:
        return jsonify({"status": "error", "message": "Ordem de serviço não encontrada."}), 404
    
    if active_service_orders[client_id]['status'] != 'orcamento aprovado':
        return jsonify({"status": "error", "message": "Serviço ainda não aprovado."}), 400

    active_service_orders[client_id]['status'] = 'executing'
    active_service_orders[client_id]['messages'].append(f"Executando serviço para o cliente {client_id}...")
    # Simula o trabalho
    time.sleep(1) # Pequena pausa para simular
    active_service_orders[client_id]['messages'].append(f"Serviço para {client_id} executado.")
    return jsonify({"status": "success", "message": "Serviço em execução."})

@app.route('/finalize_service', methods=['POST'])
def finalize_service():
    client_id = request.form['client_id']

    if client_id not in active_service_orders:
        return jsonify({"status": "error", "message": "Ordem de serviço não encontrada."}), 404
    
    service_channel = active_service_orders[client_id]['channel']
    message = f"MENSAGEM_CONCLUSAO_SERVICO|{client_id}|Serviço Concluído."
    r.publish(service_channel, message)
    
    active_service_orders[client_id]['status'] = 'completed'
    active_service_orders[client_id]['messages'].append(f"Você finalizou o serviço para {client_id}.")
    return jsonify({"status": "success", "message": "Serviço finalizado."})

@app.route('/cancel_service', methods=['POST'])
def cancel_service():
    client_id = request.form['client_id']

    if client_id not in active_service_orders:
        return jsonify({"status": "error", "message": "Ordem de serviço não encontrada."}), 404
    
    service_channel = active_service_orders[client_id]['channel']
    message = f"SERVICO_CANCELADO|{client_id}|Serviço Cancelado."
    r.publish(service_channel, message)
    
    active_service_orders[client_id]['status'] = 'cancelled'
    active_service_orders[client_id]['messages'].append(f"Você cancelou o serviço para {client_id}.")
    
    # Desassina o técnico deste canal, pois foi cancelado
    technician_pubsub.unsubscribe(service_channel)
    del active_service_orders[client_id] # Remove do rastreamento local
    return jsonify({"status": "success", "message": "Serviço cancelado."})

def listen_for_technician_messages():
    initial_requests_channel = "initial_maintenance_requests"
    technician_pubsub.subscribe(initial_requests_channel)
    print(f"Técnico {technician_id} ouvindo solicitações iniciais em '{initial_requests_channel}'...")

    for message in technician_pubsub.listen():
        if message['type'] == 'message':
            data = message['data']
            channel = message['channel']

            if data.startswith("SOLICITAR_MANUTENCAO") and channel == initial_requests_channel:
                parts = data.split('|')
                _msg_type, client_id, problem_description = parts[0], parts[1], parts[2]
                
                if client_id not in active_service_orders:
                    service_channel = f"maintenance_channel_{client_id}"
                    active_service_orders[client_id] = {
                        'problem': problem_description, 
                        'channel': service_channel, 
                        'status': 'new',
                        'messages': [f"Recebida nova solicitação do Cliente {client_id}: '{problem_description}'"],
                        'quote': None # Garante que o campo 'quote' exista para novas ordens
                    }
                    technician_pubsub.subscribe(service_channel)
                    print(f"Técnico {technician_id} assinou o canal {service_channel}")
                    
            elif channel.startswith("maintenance_channel_"):
                client_id_from_channel = channel.replace("maintenance_channel_", "")
                if client_id_from_channel in active_service_orders:
                    active_service_orders[client_id_from_channel]['messages'].append(f"Mensagem do Cliente {client_id_from_channel}: {data}")

                    if data.startswith("APROVAR_ORCAMENTO"):
                        active_service_orders[client_id_from_channel]['status'] = 'orcamento aprovado'
                        active_service_orders[client_id_from_channel]['messages'].append(f"Cliente {client_id_from_channel} aprovou o orçamento!")
                    elif data.startswith("NEGAR_ORCAMENTO"):
                        active_service_orders[client_id_from_channel]['status'] = 'orcamento negado'
                        active_service_orders[client_id_from_channel]['messages'].append(f"Cliente {client_id_from_channel} recusou o orçamento.")
                        # O técnico desassina se o cliente recusar
                        technician_pubsub.unsubscribe(channel)
                        if client_id_from_channel in active_service_orders:
                            del active_service_orders[client_id_from_channel]
                    elif data.startswith("CHANNEL_CLOSED"):
                        active_service_orders[client_id_from_channel]['messages'].append(f"Canal para o cliente {client_id_from_channel} explicitamente fechado pelo sistema.")
                        technician_pubsub.unsubscribe(channel)
                        if client_id_from_channel in active_service_orders:
                            del active_service_orders[client_id_from_channel]
        time.sleep(0.1)


if __name__ == '__main__':
    # Inicia a escuta do Redis em uma thread separada
    threading.Thread(target=listen_for_technician_messages, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)