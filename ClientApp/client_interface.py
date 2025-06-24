import redis # Importa a biblioteca Python para interagir com o Redis.
import time # Importa a biblioteca para funções relacionadas ao tempo, como pausas.
import uuid # Importa a biblioteca para gerar identificadores únicos universais (UUIDs).

# Substitua pelo IP real do seu dispositivo Android executando o Redis
REDIS_HOST = 'localhost' # Parâmetro: Endereço IP do host onde o servidor Redis está em execução.
REDIS_PORT = 6379 # Parâmetro: Porta padrão do Redis.

class ClientInterface:
    def __init__(self):
        # Conecta-se ao servidor Redis.
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True) # decode_responses=True
        self.client_id = f"cliente_{uuid.uuid4().hex[:8]}"
        self.active_channel = None
        print(f"Cliente {self.client_id} conectado ao Redis em {REDIS_HOST}:{REDIS_PORT}")

    def solicit_maintenance(self, problem_description):
        initial_channel = "initial_maintenance_requests"
        message = f"SOLICITAR_MANUTENCAO|{self.client_id}|{problem_description}"
        self.r.publish(initial_channel, message)
        print(f"\nCliente {self.client_id}: Solicitou manutenção: '{problem_description}'")
        print(f"Aguardando orçamento ou notificação do técnico...")

        self.active_channel = f"maintenance_channel_{self.client_id}"
        pubsub = self.r.pubsub()
        pubsub.subscribe(self.active_channel)
        print(f"Ouvindo atualizações no canal: {self.active_channel}")

        for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data'] # REMOVIDO .decode()
                print(f"Cliente {self.client_id} Recebido: {data}")

                # ALTERADO: Extrai o valor do orçamento da mensagem NOTIFICACAO_ORCAMENTO
                if data.startswith("NOTIFICACAO_ORCAMENTO"):
                    parts = data.split('|')
                    if len(parts) > 2: # Espera "NOTIFICACAO_ORCAMENTO|client_id|quote_amount"
                        quote_amount = parts[2]
                        print(f"Notificação de orçamento recebida: R$ {quote_amount}. Aprovar ou recusar?")
                    else:
                        print("Notificação de orçamento recebida. Aprovar ou recusar?") # Fallback

                    response = input("Digite 'aprovar' para aprovar, 'negar' para recusar: ").lower()
                    if response == 'aprovar':
                        self.r.publish(self.active_channel, f"APROVAR_ORCAMENTO|{self.client_id}|Orçamento aprovado.")
                        print("Aprovação enviada ao técnico.")
                    else:
                        self.r.publish(self.active_channel, f"NEGAR_ORCAMENTO|{self.client_id}|Orçamento negado.")
                        print("Recusa enviada ao técnico.")
                elif "NOTIFICACAO_CONCLUSAO" in data:
                    print("Serviço concluído! Obrigado!")
                    pubsub.unsubscribe(self.active_channel)
                    self.active_channel = None
                    break
                elif "SERVICO_CANCELADO" in data:
                    print("Serviço foi cancelado.")
                    pubsub.unsubscribe(self.active_channel)
                    self.active_channel = None
                    break
                elif "CHANNEL_CLOSED" in data:
                    print(f"Canal {self.active_channel} explicitamente fechado pelo sistema.")
                    pubsub.unsubscribe(self.active_channel)
                    self.active_channel = None
                    break
            time.sleep(0.1)

if __name__ == "__main__":
    client = ClientInterface()
    while True:
        problem = input("Digite a solicitação de manutenção (ex: 'vazamento na torneira') ou 'sair' para sair: ")
        if problem.lower() == 'sair':
            break
        client.solicit_maintenance(problem)
        print("\n--- Nova solicitação de manutenção ---")