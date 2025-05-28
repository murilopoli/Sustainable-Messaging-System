import time # Importa a biblioteca para funções relacionadas ao tempo (usada para timestamp).

# Este é um banco de dados simples em memória para fins de demonstração.
# Em um ambiente de produção, este seria um banco de dados persistente (ex: MySQL, PostgreSQL).

class ServiceOrderDatabase:
    def __init__(self):
        # Dicionário em memória para armazenar ordens de serviço.
        # Chave: client_id. Valor: Dicionário com detalhes da ordem de serviço.
        self.service_orders = {}  # {client_id: {problem: "...", quote: "...", status: "..."}}
        print("Banco de Dados de Ordem de Serviço inicializado (em memória).") # Mensagem de inicialização.

    def create_service_order(self, client_id, problem_description):
        # Parâmetros: client_id (ID único do cliente), problem_description (descrição do problema).
        if client_id in self.service_orders: # Verifica se já existe uma ordem de serviço para este cliente.
            print(f"Ordem de serviço para {client_id} já existe. Atualizando...") # Mensagem se já existe.
            # Se existir, atualiza apenas o problema e redefine o status.
            self.service_orders[client_id].update({'problem': problem_description, 'status': 'new_request'})
        else: # Se não existir, cria uma nova ordem de serviço.
            self.service_orders[client_id] = {
                'problem': problem_description,
                'quote': None, # Inicialmente sem orçamento.
                'status': 'new_request', # Semântica: Status inicial da ordem de serviço.
                                        # Possíveis status: 'new_request', 'orcamento emitido', 'orcamento aprovado', 'executing', 'concluida', 'cancelada'
                'created_at': time.time() # Timestamp da criação da ordem de serviço.
            }
        print(f"DB: Ordem de serviço criada/atualizada para {client_id}.") # Confirmação da operação.

    def update_service_order(self, client_id, updates):
        # Parâmetros: client_id, updates (dicionário com os campos a serem atualizados).
        if client_id in self.service_orders: # Verifica se a ordem de serviço existe.
            self.service_orders[client_id].update(updates) # Ação: Atualiza os campos da ordem de serviço.
            print(f"DB: Ordem de serviço atualizada para {client_id}. Novo status: {self.service_orders[client_id]['status']}") # Informa a atualização.
            return True # Retorna True se a atualização foi bem-sucedida.
        print(f"DB Erro: Ordem de serviço para {client_id} não encontrada.") # Mensagem de erro se não encontrada.
        return False # Retorna False se a ordem de serviço não foi encontrada.

    def get_service_order(self, client_id):
        # Parâmetro: client_id.
        # Retorna os detalhes da ordem de serviço para o cliente dado, ou None se não encontrada.
        return self.service_orders.get(client_id)

    def list_service_orders(self):
        # Retorna todas as ordens de serviço atualmente armazenadas no banco de dados em memória.
        return self.service_orders