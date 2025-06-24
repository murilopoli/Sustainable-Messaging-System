import redis # Importa a biblioteca Python para interagir com o Redis.
import time # Importa a biblioteca para funções relacionadas ao tempo, como pausas.

# Substitua pelo IP real do seu dispositivo Android executando o Redis
REDIS_HOST = 'localhost' # Parâmetro: Endereço IP do host onde o servidor Redis está em execução.
REDIS_PORT = 6379 # Parâmetro: Porta padrão do Redis.

class MessagingConsumer:
    def __init__(self):
        # Conecta-se ao servidor Redis.
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        self.pubsub = self.r.pubsub() # Cria uma instância de PubSub para gerenciar assinaturas.
        self.subscribed_channels = set() # Contexto: Conjunto para armazenar os nomes dos canais atualmente assinados.
        print(f"Serviço de Mensageria conectado ao Redis em {REDIS_HOST}:{REDIS_PORT}") # Informa a conexão.

        # Assina inicialmente um canal onde novos pedidos de serviço são anunciados
        # Semântica: Este canal é usado por outros serviços (ex: ServiceOrderService) para notificar o MessagingService
        # sobre a criação de novos canais específicos para clientes.
        self.pubsub.subscribe("new_service_announcements")
        self.subscribed_channels.add("new_service_announcements") # Adiciona o canal ao conjunto de canais assinados.
        print(f"Ouvindo novos anúncios de serviço em 'new_service_announcements'...") # Informa sobre a escuta.

    def listen_for_messages(self):
        # Loop principal para escutar mensagens em todos os canais assinados.
        for message in self.pubsub.listen():
            if message['type'] == 'message': # Verifica se a mensagem é do tipo 'message'.
                data = message['data'] # REMOVIDO .decode()
                channel = message['channel'] # REMOVIDO .decode()

                # Se for um novo anúncio de serviço, assine o canal específico do cliente
                if channel == "new_service_announcements" and data.startswith("NEW_SERVICE_CHANNEL_CREATED"): # Verifica se é um anúncio de novo canal.
                    parts = data.split('|') # Divide a string da mensagem.
                    _msg_type, client_id, new_channel_name = parts[0], parts[1], parts[2] # Atribui as partes.
                    if new_channel_name not in self.subscribed_channels: # Evita assinar o mesmo canal múltiplas vezes.
                        self.pubsub.subscribe(new_channel_name) # Assina o novo canal específico do cliente.
                        self.subscribed_channels.add(new_channel_name) # Adiciona ao conjunto de canais assinados.
                        print(f"Serviço de Mensageria: Assinado o canal do cliente {new_channel_name} para o cliente {client_id}.") # Confirmação.
                elif channel in self.subscribed_channels: # Se a mensagem veio de um canal já assinado (ou seja, um canal de cliente).
                    # Lida com mensagens em canais específicos do cliente
                    if data.startswith("MENSAGEM_ORCAMENTO"): # Semântica: Mensagem de orçamento.
                        parts = data.split('|')
                        _msg_type, client_id, quote_amount = parts[0], parts[1], parts[2]
                        print(f"Serviço de Mensageria: Notificando Cliente {client_id}: 'Seu orçamento é R$ {quote_amount}.'") # Notificação para console.
                        # ALTERADO: Inclui o quote_amount na notificação para o cliente
                        self.r.publish(f"maintenance_channel_{client_id}", f"NOTIFICACAO_ORCAMENTO|{client_id}|{quote_amount}")
                    elif data.startswith("MENSAGEM_APROVACAO_ORCAMENTO"): # Semântica: Mensagem de aprovação de orçamento.
                        parts = data.split('|')
                        _msg_type, client_id, _status = parts[0], parts[1], parts[2]
                        print(f"Serviço de Mensageria: Notificando Cliente {client_id}: 'Orçamento aprovado pelo sistema.'") # Notificação para console.
                        self.r.publish(f"maintenance_channel_{client_id}", f"NOTIFICACAO_APROVACAO_ORCAMENTO|{client_id}|Orçamento aprovado.")
                    elif data.startswith("MENSAGEM_CONCLUSAO_SERVICO"): # Semântica: Mensagem de conclusão de serviço.
                        parts = data.split('|')
                        _msg_type, client_id, _status = parts[0], parts[1], parts[2]
                        print(f"Serviço de Mensageria: Notificando Cliente {client_id}: 'O serviço foi concluído!'") # Notificação para console.
                        # Envia notificação final para o ClientApp.
                        self.r.publish(f"maintenance_channel_{client_id}", f"NOTIFICACAO_CONCLUSAO|{client_id}|Serviço concluído.")
                    elif data.startswith("SERVICO_CANCELADO"): # Semântica: Mensagem de serviço cancelado.
                        parts = data.split('|')
                        _msg_type, client_id, _status = parts[0], parts[1], parts[2]
                        print(f"Serviço de Mensageria: Notificando Cliente {client_id}: 'O serviço foi cancelado.'") # Notificação para console.
                        self.r.publish(f"maintenance_channel_{client_id}", f"SERVICO_CANCELADO|{client_id}|Serviço Cancelado.")
                    elif data == 'exit' or data.startswith("CHANNEL_CLOSED"): # Semântica: Sinal para o consumidor parar de ouvir este canal.
                        # Se um canal receber um sinal 'exit' ou 'CHANNEL_CLOSED', cancele a assinatura
                        client_id = channel.replace("maintenance_channel_", "") # Extrai o ID do cliente do nome do canal.
                        print(f"Serviço de Mensageria: Recebido sinal de saída para o canal {channel}. Cancelando assinatura...") # Informa sobre o sinal.
                        self.pubsub.unsubscribe(channel) # Ação: Desassina do canal.
                        self.subscribed_channels.remove(channel) # Remove o canal do conjunto de canais assinados.
                        # Opcionalmente, notifica o cliente que sua sessão foi concluída, se ainda não o fez
                        if data == 'exit': # 'CHANNEL_CLOSED' já é uma notificação do cliente do SO Service
                            self.r.publish(f"maintenance_channel_{client_id}", f"CHANNEL_CLOSED|{client_id}|Sessão de comunicação finalizada.") # Envia uma última notificação ao cliente.


            time.sleep(0.1) # Pausa curta para evitar consumo excessivo de CPU.

# Bloco executado quando o script é o principal.
if __name__ == "__main__":
    consumer = MessagingConsumer() # Cria uma instância do consumidor de mensageria.
    try:
        consumer.listen_for_messages() # Inicia o loop de escuta por mensagens.
    except KeyboardInterrupt: # Captura a interrupção de teclado (Ctrl+C).
        print("\nServiço de Mensageria sendo encerrado.") # Mensagem de encerramento.
        for channel in list(consumer.subscribed_channels): # Itera sobre uma cópia do conjunto de canais para evitar modificação durante a iteração.
            consumer.pubsub.unsubscribe(channel) # Desassina de todos os canais ativos.
        consumer.r.close() # Fecha a conexão Redis.