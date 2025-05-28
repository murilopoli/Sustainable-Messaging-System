import redis # Importa a biblioteca Python para interagir com o Redis.
import time # Importa a biblioteca para funções relacionadas ao tempo, como pausas.
from service_order_db import ServiceOrderDatabase # Importa a classe do banco de dados de ordens de serviço.

# Substitua pelo IP real do seu dispositivo Android executando o Redis
REDIS_HOST = 'localhost' # Parâmetro: Endereço IP do host onde o servidor Redis está em execução.
REDIS_PORT = 6379 # Parâmetro: Porta padrão do Redis.

class ServiceOrderConsumer:
    def __init__(self):
        # Conecta-se ao servidor Redis.
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0) # Conecta-se ao DB 0 do Redis.
        self.pubsub = self.r.pubsub() # Cria uma instância de PubSub para gerenciar assinaturas.
        self.db = ServiceOrderDatabase() # Cria uma instância do banco de dados de ordens de serviço.
        self.subscribed_channels = set() # Contexto: Conjunto para armazenar os nomes dos canais atualmente assinados.
        print(f"Serviço de Ordem de Serviço conectado ao Redis em {REDIS_HOST}:{REDIS_PORT}") # Informa a conexão.

        # Assina um canal geral onde novos pedidos de serviço são anunciados
        # Semântica: Este canal é usado por este serviço para notificar outros serviços
        # sobre a criação de novos canais específicos para clientes.
        self.pubsub.subscribe("new_service_announcements")
        self.subscribed_channels.add("new_service_announcements") # Adiciona o canal ao conjunto de canais assinados.
        print(f"Ouvindo novos anúncios de serviço em 'new_service_announcements'...") # Informa sobre a escuta.

        # Também assina o canal de solicitações iniciais de manutenção para criar SOs diretamente
        # Semântica: Permite que este serviço capture a solicitação inicial do cliente
        # e inicie o processo de criação da ordem de serviço.
        self.pubsub.subscribe("initial_maintenance_requests")
        self.subscribed_channels.add("initial_maintenance_requests") # Adiciona o canal ao conjunto de canais assinados.
        print(f"Ouvindo solicitações iniciais de manutenção em 'initial_maintenance_requests'...") # Informa sobre a escuta.


    def listen_for_messages(self):
        # Loop principal para escutar mensagens em todos os canais assinados.
        for message in self.pubsub.listen():
            if message['type'] == 'message': # Verifica se a mensagem é do tipo 'message'.
                data = message['data'].decode() # Decodifica os dados da mensagem.
                channel = message['channel'].decode() # Decodifica o nome do canal de onde a mensagem veio.

                # Lida com solicitações iniciais de manutenção (alternativa a NEW_SERVICE_CHANNEL_CREATED para criação direta de SO)
                if channel == "initial_maintenance_requests" and data.startswith("SOLICITAR_MANUTENCAO"): # Verifica se é uma solicitação inicial.
                    parts = data.split('|') # Divide a string da mensagem.
                    _msg_type, client_id, problem_description = parts[0], parts[1], parts[2] # Atribui as partes.
                    new_channel_name = f"maintenance_channel_{client_id}" # Cria o nome do canal específico do cliente.
                    if new_channel_name not in self.subscribed_channels: # Evita assinar o mesmo canal múltiplas vezes.
                        self.pubsub.subscribe(new_channel_name) # Assina o novo canal específico do cliente.
                        self.subscribed_channels.add(new_channel_name) # Adiciona ao conjunto de canais assinados.
                        print(f"Serviço de Ordem de Serviço: Assinado o canal do cliente {new_channel_name} para o cliente {client_id}.") # Confirmação.
                    # Anuncia que um novo canal é criado para outros serviços (ex: MessagingService) assinarem.
                    self.r.publish("new_service_announcements", f"NEW_SERVICE_CHANNEL_CREATED|{client_id}|{new_channel_name}")
                    self.db.create_service_order(client_id, problem_description) # Ação: Cria a ordem de serviço no banco de dados.
                    print(f"Serviço de Ordem de Serviço: Ordem de serviço criada para o cliente {client_id}. Status: {self.db.get_service_order(client_id)['status']}") # Informa a criação.
                    self.r.publish(new_channel_name, f"ORDEM_DE_SERVICO_CRIADA|{client_id}|SO criada.") # Publica a confirmação de criação da SO no canal do cliente.

                # Lida com mensagens em canais específicos do cliente
                elif channel in self.subscribed_channels: # Se a mensagem veio de um canal já assinado (ou seja, um canal de cliente).
                    if data.startswith("MENSAGEM_ORCAMENTO"): # Semântica: Mensagem de orçamento.
                        parts = data.split('|')
                        _msg_type, client_id, quote_amount = parts[0], parts[1], parts[2]
                        # Ação: Atualiza a ordem de serviço no banco de dados com o orçamento e status.
                        self.db.update_service_order(client_id, {'quote': quote_amount, 'status': 'orcamento emitido'})
                        print(f"Serviço de Ordem de Serviço: SO atualizada para {client_id} com orçamento {quote_amount}. Status: {self.db.get_service_order(client_id)['status']}") # Informa a atualização.
                        # Publica a atualização da SO no canal do cliente.
                        self.r.publish(f"maintenance_channel_{client_id}", f"ATUALIZAR_ORDEM_DE_SERVICO|{client_id}|SO atualizada com orçamento.")
                    elif data.startswith("APROVAR_ORCAMENTO"): # Semântica: Mensagem de aprovação de orçamento.
                        parts = data.split('|')
                        _msg_type, client_id, _response = parts[0], parts[1], parts[2]
                        # Ação: Atualiza o status da ordem de serviço para 'aprovado'.
                        self.db.update_service_order(client_id, {'status': 'orcamento aprovado'})
                        print(f"Serviço de Ordem de Serviço: SO para {client_id} aprovada. Status: {self.db.get_service_order(client_id)['status']}") # Informa a aprovação.
                        self.r.publish(f"maintenance_channel_{client_id}", f"ORDEM_DE_SERVICO_ATUALIZADA|{client_id}|Status da SO atualizado.")
                    elif data.startswith("NEGAR_ORCAMENTO"): # Semântica: Mensagem de recusa de orçamento.
                        parts = data.split('|')
                        _msg_type, client_id, _response = parts[0], parts[1], parts[2]
                        # Ação: Atualiza o status da ordem de serviço para 'cancelada'.
                        self.db.update_service_order(client_id, {'status': 'cancelada'})
                        print(f"Serviço de Ordem de Serviço: SO para {client_id} recusada. Status: {self.db.get_service_order(client_id)['status']}") # Informa a recusa.
                        self.r.publish(f"maintenance_channel_{client_id}", f"ORDEM_DE_SERVICO_CANCELADA|{client_id}|SO cancelada.")
                        self.close_channel(client_id, channel) # Ação: Chama a função para fechar o canal.
                    elif data.startswith("MENSAGEM_CONCLUSAO_SERVICO"): # Semântica: Mensagem de conclusão de serviço.
                        parts = data.split('|')
                        _msg_type, client_id, _status_msg = parts[0], parts[1], parts[2]
                        # Ação: Atualiza o status da ordem de serviço para 'concluida'.
                        self.db.update_service_order(client_id, {'status': 'concluida'})
                        print(f"Serviço de Ordem de Serviço: SO para {client_id} concluída. Status: {self.db.get_service_order(client_id)['status']}") # Informa a conclusão.
                        self.r.publish(f"maintenance_channel_{client_id}", f"ORDEM_DE_SERVICO_CONCLUIDA|{client_id}|SO concluída.")
                        self.close_channel(client_id, channel) # Ação: Chama a função para fechar o canal.
                    elif data.startswith("SERVICO_CANCELADO"): # Semântica: Mensagem de serviço cancelado diretamente.
                        parts = data.split('|')
                        _msg_type, client_id, _status_msg = parts[0], parts[1], parts[2]
                        # Ação: Atualiza o status da ordem de serviço para 'cancelada'.
                        self.db.update_service_order(client_id, {'status': 'cancelada'})
                        print(f"Serviço de Ordem de Serviço: SO para {client_id} diretamente cancelada. Status: {self.db.get_service_order(client_id)['status']}") # Informa o cancelamento.
                        self.close_channel(client_id, channel) # Ação: Chama a função para fechar o canal.
                    elif data == 'exit': # Sinal para o próprio consumidor parar de ouvir este canal (geralmente de outro serviço).
                        print(f"Serviço de Ordem de Serviço: Recebido sinal de saída para o canal {channel}. Cancelando assinatura...") # Informa sobre o sinal.
                        self.pubsub.unsubscribe(channel) # Desassina do canal.
                        self.subscribed_channels.remove(channel) # Remove do conjunto de canais assinados.


            time.sleep(0.1) # Pausa curta para evitar consumo excessivo de CPU.

    def close_channel(self, client_id, channel_name):
        # Notifica todos os ouvintes neste canal específico para parar
        # Semântica: Envia uma mensagem final para que todos os consumidores saibam que o canal será fechado.
        self.r.publish(channel_name, f"CHANNEL_CLOSED|{client_id}")
        # Desassina o próprio ServiceOrderService
        self.pubsub.unsubscribe(channel_name) # Ação: Desassina do canal.
        if channel_name in self.subscribed_channels: # Verifica se o canal ainda está no conjunto.
            self.subscribed_channels.remove(channel_name) # Remove o canal do conjunto de canais assinados.
        print(f"Serviço de Ordem de Serviço: Canal {channel_name} fechado para o cliente {client_id}.") # Confirmação do fechamento.


# Bloco executado quando o script é o principal.
if __name__ == "__main__":
    consumer = ServiceOrderConsumer() # Cria uma instância do consumidor de ordem de serviço.
    try:
        consumer.listen_for_messages() # Inicia o loop de escuta por mensagens.
    except KeyboardInterrupt: # Captura a interrupção de teclado (Ctrl+C).
        print("\nServiço de Ordem de Serviço sendo encerrado.") # Mensagem de encerramento.
        for channel in list(consumer.subscribed_channels): # Itera sobre uma cópia do conjunto de canais.
            consumer.pubsub.unsubscribe(channel) # Desassina de todos os canais ativos.
        consumer.r.close() # Fecha a conexão Redis.
