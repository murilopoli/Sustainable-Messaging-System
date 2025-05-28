import redis # Importa a biblioteca Python para interagir com o Redis.
import time # Importa a biblioteca para funções relacionadas ao tempo, como pausas.
import uuid # Importa a biblioteca para gerar identificadores únicos universais (UUIDs).

# Substitua pelo IP real do seu dispositivo Android executando o Redis
REDIS_HOST = 'localhost' # Parâmetro: Endereço IP do host onde o servidor Redis está em execução.
REDIS_PORT = 6379 # Parâmetro: Porta padrão do Redis.

class TechnicianInterface:
    def __init__(self):
        # Conecta-se ao servidor Redis.
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0) # Conecta-se ao DB 0 do Redis.
        self.technician_id = f"tecnico_{uuid.uuid4().hex[:8]}" # Gera um ID único para este técnico.
        self.active_service_orders = {} # Contexto: Dicionário para rastrear ordens de serviço ativas.
                                       # Chave: ID do cliente. Valor: Dicionário com 'channel' e 'status'.

        # Assina um canal geral para solicitações iniciais de clientes.
        # Semântica: Este canal é o ponto de entrada para novas solicitações.
        self.initial_requests_channel = "initial_maintenance_requests"
        self.pubsub = self.r.pubsub() # Cria uma instância de PubSub para gerenciar assinaturas.
        self.pubsub.subscribe(self.initial_requests_channel) # Assina o canal de solicitações iniciais.
        print(f"Técnico {self.technician_id} conectado ao Redis em {REDIS_HOST}:{REDIS_PORT}") # Informa a conexão.
        print(f"Ouvindo solicitações iniciais de manutenção em '{self.initial_requests_channel}'...") # Informa sobre a escuta.

    def listen_for_messages(self):
        # Loop principal para escutar mensagens em todos os canais assinados (geral e específicos).
        for message in self.pubsub.listen():
            if message['type'] == 'message': # Verifica se a mensagem é do tipo 'message'.
                data = message['data'].decode() # Decodifica os dados da mensagem.
                # Lida com solicitações iniciais de manutenção
                if data.startswith("SOLICITAR_MANUTENCAO"): # Semântica: Identifica uma nova solicitação de manutenção.
                    parts = data.split('|') # Divide a string da mensagem em partes.
                    _msg_type, client_id, problem_description = parts[0], parts[1], parts[2] # Atribui as partes a variáveis.
                    print(f"\nRecebida nova solicitação de manutenção do Cliente {client_id}: '{problem_description}'") # Exibe a solicitação.
                    self.initiate_service(client_id, problem_description) # Chama a função para iniciar o serviço.
                # Lida com respostas em canais específicos do cliente
                # 'any(... for cid in self.active_service_orders)' verifica se a mensagem começa com uma aprovação/recusa para *qualquer* cliente ativo.
                elif any(data.startswith(f"APROVAR_ORCAMENTO|{cid}") for cid in self.active_service_orders):
                    parts = data.split('|')
                    _msg_type, client_id, _response = parts[0], parts[1], parts[2]
                    if client_id in self.active_service_orders: # Verifica se o ID do cliente está entre as ordens de serviço ativas.
                        self.active_service_orders[client_id]['status'] = ' orçamento aprovado' # Atualiza o status local.
                        print(f"Cliente {client_id} aprovou o orçamento!") # Confirmação.
                        self.execute_service(client_id) # Chama a função para executar o serviço.
                elif any(data.startswith(f"NEGAR_ORCAMENTO|{cid}") for cid in self.active_service_orders):
                    parts = data.split('|')
                    _msg_type, client_id, _response = parts[0], parts[1], parts[2]
                    if client_id in self.active_service_orders:
                        self.active_service_orders[client_id]['status'] = ' orçamento negado' # Atualiza o status local.
                        print(f"Cliente {client_id} recusou o orçamento.") # Confirmação.
                        self.cancel_service(client_id) # Chama a função para cancelar o serviço.
                elif data.startswith("CHANNEL_CLOSED"): # Semântica: Indica que o canal específico foi fechado pelo sistema.
                    parts = data.split('|')
                    _msg_type, client_id = parts[0], parts[1]
                    if client_id in self.active_service_orders:
                        print(f"Canal para o cliente {client_id} explicitamente fechado pelo sistema.") # Informa sobre o fechamento.
                        # O técnico não precisa fazer mais nada para este canal
                        # pois já é tratado pelo MessagingService/ServiceOrderService.
                        del self.active_service_orders[client_id] # Remove a ordem de serviço do rastreamento local.

            time.sleep(0.1) # Pausa curta para evitar consumo excessivo de CPU.

    def initiate_service(self, client_id, problem_description):
        # O técnico inicia um novo serviço, criando um canal específico para este cliente
        service_channel = f"maintenance_channel_{client_id}" # Constrói o nome do canal específico.
        # Adiciona a nova ordem de serviço ao dicionário de rastreamento do técnico.
        self.active_service_orders[client_id] = {'channel': service_channel, 'status': 'new'}
        # O técnico assina este novo canal para receber respostas do cliente
        self.pubsub.subscribe(service_channel) # Assina o canal recém-criado.

        message = f"NOVO_SERVICO|{client_id}|{problem_description}" # Mensagem de novo serviço.
        self.r.publish(service_channel, message) # Publica a mensagem no canal específico.
        print(f"Técnico iniciou novo serviço para {client_id} no canal {service_channel}.") # Confirmação.
        self.emit_quote(client_id) # Chama a função para emitir o orçamento.

    def emit_quote(self, client_id):
        if client_id not in self.active_service_orders: # Verifica se a ordem de serviço existe.
            print(f"Erro: Nenhum serviço ativo para o cliente {client_id}") # Mensagem de erro.
            return # Sai da função.

        quote_amount = input(f"Digite o valor do orçamento para {client_id}: ") # Parâmetro: Entrada do valor do orçamento.
        quote_message = f"MENSAGEM_ORCAMENTO|{client_id}|{quote_amount}" # Constrói a mensagem de orçamento.
        self.r.publish(self.active_service_orders[client_id]['channel'], quote_message) # Publica o orçamento.
        self.active_service_orders[client_id]['status'] = 'quote sent' # Atualiza o status local.
        print(f"Técnico emitiu orçamento para {client_id}: {quote_amount}. Aguardando aprovação.") # Confirmação.

    def execute_service(self, client_id):
        if client_id not in self.active_service_orders:
            print(f"Erro: Nenhum serviço ativo para o cliente {client_id}")
            return
        if self.active_service_orders[client_id]['status'] != ' orçamento aprovado': # Verifica se o orçamento foi aprovado.
            print(f"Serviço para {client_id} ainda não aprovado. Não é possível executar.")
            return

        print(f"Executando serviço para o cliente {client_id}...") # Mensagem de início de execução.
        # Simula o trabalho
        time.sleep(2) # Pausa de 2 segundos para simular a execução do serviço.
        self.active_service_orders[client_id]['status'] = 'executing' # Atualiza o status local.
        print(f"Serviço para {client_id} executado.") # Confirmação.
        self.finalize_service(client_id) # Chama a função para finalizar o serviço.

    def finalize_service(self, client_id):
        if client_id not in self.active_service_orders:
            print(f"Erro: Nenhum serviço ativo para o cliente {client_id}")
            return

        message = f"MENSAGEM_CONCLUSAO_SERVICO|{client_id}|Serviço Concluído." # Mensagem de conclusão do serviço.
        self.r.publish(self.active_service_orders[client_id]['channel'], message) # Publica a mensagem de conclusão.
        self.active_service_orders[client_id]['status'] = 'completed' # Atualiza o status local.
        print(f"Técnico finalizou o serviço para {client_id}. Mensagem enviada para o barramento.") # Confirmação.
        # O canal será fechado pelo ServiceOrderService ou uma camada de orquestração (não pelo técnico diretamente aqui).

    def cancel_service(self, client_id):
        if client_id not in self.active_service_orders:
            print(f"Erro: Nenhum serviço ativo para o cliente {client_id}")
            return
        message = f"SERVICO_CANCELADO|{client_id}|Serviço Cancelado." # Mensagem de serviço cancelado.
        self.r.publish(self.active_service_orders[client_id]['channel'], message) # Publica a mensagem de cancelamento.
        self.active_service_orders[client_id]['status'] = 'cancelled' # Atualiza o status local.
        print(f"Técnico cancelou o serviço para {client_id}.") # Confirmação.
        # Desassina o técnico deste canal, pois foi cancelado
        self.pubsub.unsubscribe(self.active_service_orders[client_id]['channel']) # Remove a assinatura do canal.
        del self.active_service_orders[client_id] # Remove a ordem de serviço do rastreamento local.


# Bloco executado quando o script é o principal.
if __name__ == "__main__":
    technician = TechnicianInterface() # Cria uma instância da interface do técnico.
    try:
        technician.listen_for_messages() # Inicia o loop de escuta por mensagens.
    except KeyboardInterrupt: # Captura a interrupção de teclado (Ctrl+C).
        print("\nInterface do técnico sendo encerrada.") # Mensagem de encerramento.
        technician.pubsub.unsubscribe(technician.initial_requests_channel) # Desassina do canal inicial.
        for so in technician.active_service_orders.values(): # Itera sobre as ordens de serviço ativas.
            technician.pubsub.unsubscribe(so['channel']) # Desassina de todos os canais de ordens de serviço ativas.
        technician.r.close() # Fecha a conexão Redis.
