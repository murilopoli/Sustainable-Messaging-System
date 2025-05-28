import redis # Importa a biblioteca Python para interagir com o Redis.
import time # Importa a biblioteca para funções relacionadas ao tempo, como pausas.
import uuid # Importa a biblioteca para gerar identificadores únicos universais (UUIDs).

# Substitua pelo IP real do seu dispositivo Android executando o Redis
REDIS_HOST = '192.168.1.7' # Parâmetro: Endereço IP do host onde o servidor Redis está em execução.
REDIS_PORT = 6379 # Parâmetro: Porta padrão do Redis.

class ClientInterface:
    def __init__(self):
        # Conecta-se ao servidor Redis.
        # self.r é a instância do cliente Redis que permite publicar e assinar mensagens.
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0) # db=0 seleciona o banco de dados padrão do Redis.
        # Gera um ID único para este cliente usando UUID (ex: 'cliente_abcdef12').
        self.client_id = f"cliente_{uuid.uuid4().hex[:8]}" # Semântica: Identificação única para cada instância do cliente.
        self.active_channel = None # Contexto: Armazena o nome do canal Redis específico para a solicitação de manutenção atual do cliente. Inicialmente nulo.
        print(f"Cliente {self.client_id} conectado ao Redis em {REDIS_HOST}:{REDIS_PORT}") # Informa a conexão.

    def solicit_maintenance(self, problem_description):
        # Um cliente solicita manutenção, esta mensagem vai para o TechnicianApp.
        # Não criamos um canal específico ainda, pois o técnico o iniciará.
        # Para simplificar, usamos um canal geral para o contato inicial.
        initial_channel = "initial_maintenance_requests" # Contexto: Canal genérico para a solicitação inicial.
        # Constrói a mensagem com tipo, ID do cliente e descrição do problema.
        message = f"SOLICITAR_MANUTENCAO|{self.client_id}|{problem_description}" # Semântica: Formato da mensagem para fácil parsing.
        self.r.publish(initial_channel, message) # Ação: Publica a mensagem no canal inicial.
        print(f"\nCliente {self.client_id}: Solicitou manutenção: '{problem_description}'") # Confirmação da solicitação.
        print(f"Aguardando orçamento ou notificação do técnico...") # Informa que o cliente está aguardando.

        # Agora, assine um canal específico para este cliente para receber atualizações
        # O nome do canal é dinâmico, baseado no ID do cliente, para comunicação ponto a ponto.
        self.active_channel = f"maintenance_channel_{self.client_id}" # Semântica: Canal exclusivo para esta interação cliente-serviço.
        pubsub = self.r.pubsub() # Cria uma instância de PubSub para assinar canais.
        pubsub.subscribe(self.active_channel) # Assina o canal específico do cliente.
        print(f"Ouvindo atualizações no canal: {self.active_channel}") # Informa o canal que está sendo ouvido.

        for message in pubsub.listen(): # Loop infinito para escutar mensagens no canal assinado.
            if message['type'] == 'message': # Verifica se a mensagem recebida é do tipo 'message' (não 'subscribe', 'unsubscribe' etc.).
                data = message['data'].decode() # Decodifica os dados da mensagem (que vêm em bytes) para string.
                print(f"Cliente {self.client_id} Recebido: {data}") # Exibe a mensagem recebida.

                if "NOTIFICACAO_ORCAMENTO" in data: # Semântica: Verifica se a mensagem é uma notificação de orçamento.
                    print("Notificação de orçamento recebida. Aprovar ou recusar?") # Solicita a ação do usuário.
                    response = input("Digite 'aprovar' para aprovar, 'negar' para recusar: ").lower() # Parâmetro: Entrada do usuário para aprovação/recusa.
                    if response == 'aprovar': # Condicional: Se o cliente aprovar.
                        # Cliente aprova, envia mensagem de volta ao técnico via o mesmo canal
                        # Publica a aprovação no canal ativo.
                        self.r.publish(self.active_channel, f"APROVAR_ORCAMENTO|{self.client_id}|Orçamento aprovado.")
                        print("Aprovação enviada ao técnico.") # Confirmação.
                    else: # Condicional: Se o cliente recusar.
                        # Publica a recusa no canal ativo.
                        self.r.publish(self.active_channel, f"NEGAR_ORCAMENTO|{self.client_id}|Orçamento negado.")
                        print("Recusa enviada ao técnico.") # Confirmação.
                elif "NOTIFICACAO_CONCLUSAO" in data: # Semântica: Verifica se a mensagem é uma notificação de conclusão.
                    print("Serviço concluído! Obrigado!") # Mensagem de agradecimento.
                    # Sinaliza para parar de ouvir esta solicitação de serviço
                    pubsub.unsubscribe(self.active_channel) # Ação: Desassina o canal ativo.
                    self.active_channel = None # Reseta o canal ativo.
                    break # Sai do loop de escuta, pois o serviço foi concluído.
                elif "SERVICO_CANCELADO" in data: # Semântica: Verifica se a mensagem indica que o serviço foi cancelado.
                    print("Serviço foi cancelado.") # Informa sobre o cancelamento.
                    pubsub.unsubscribe(self.active_channel) # Desassina o canal ativo.
                    self.active_channel = None # Reseta o canal ativo.
                    break # Sai do loop de escuta.
                elif "CHANNEL_CLOSED" in data: # Semântica: Verifica se a mensagem indica que o canal foi explicitamente fechado pelo sistema (geralmente pelo SO Service).
                    print(f"Canal {self.active_channel} explicitamente fechado pelo sistema.") # Informa sobre o fechamento do canal.
                    pubsub.unsubscribe(self.active_channel) # Desassina o canal ativo.
                    self.active_channel = None # Reseta o canal ativo.
                    break # Sai do loop de escuta.
            time.sleep(0.1) # Pausa curta para evitar consumo excessivo de CPU.

# Bloco executado quando o script é o principal.
if __name__ == "__main__":
    client = ClientInterface() # Cria uma instância da interface do cliente.
    while True: # Loop principal para permitir múltiplas solicitações.
        problem = input("Digite a solicitação de manutenção (ex: 'vazamento na torneira') ou 'sair' para sair: ") # Solicita a entrada do usuário.
        if problem.lower() == 'sair': # Condicional: Verifica se o usuário quer sair.
            break # Sai do loop principal.
        client.solicit_maintenance(problem) # Chama o método para solicitar manutenção.
        print("\n--- Nova solicitação de manutenção ---") # Separador para novas solicitações.