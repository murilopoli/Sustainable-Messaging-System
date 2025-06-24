# Sistema de Mensagens Sustentável - Barramento de Serviços Android

Este projeto implementa um sistema de mensageria que utiliza um Barramento de Serviços (Service Bus) em um dispositivo Android, simulando o fluxo de uma solicitação de manutenção desde o cliente até a finalização do serviço pelo técnico. A arquitetura é baseada em microsserviços que se comunicam de forma assíncrona através do Redis.

---

## 1. Visão Geral da Arquitetura e Componentes

A aplicação é modular, dividida em microsserviços e interfaces de usuário, todos se comunicando através de um servidor Redis central, atuando como um Barramento de Serviços (Service Bus).

### 1.1. Barramento de Serviços (Redis)

* **Função**: Atua como o `message broker` central, permitindo a comunicação assíncrona entre os diferentes serviços através do modelo Publish/Subscribe (Pub/Sub). É executado em um dispositivo Android para simular um ambiente de Service Bus móvel.

### 1.2. Serviços de Backend

São aplicações Python que rodam em terminais separados e processam as mensagens do barramento.

* **`ServiceOrderService`**:
    * **Localização**: `ServiceOrderService/`
    * **Função**: Gerencia o ciclo de vida das ordens de serviço. Responsável por criar, atualizar (com orçamento, aprovação, conclusão, cancelamento) e persistir o estado das ordens de serviço em um banco de dados em memória (para esta demonstração). Também gerencia o fechamento de canais específicos de clientes quando o serviço é finalizado.
* **`MessagingService`**:
    * **Localização**: `MessagingService/`
    * **Função**: Atua como um serviço de notificação. Ele intermedeia mensagens, repassando informações de status (como orçamentos e conclusões) aos clientes de forma formatada.
* **`TechnicianApp` (Console)**:
    * **Localização**: `TechnicianApp/`
    * **Função**: Simula a lógica do aplicativo do técnico em um ambiente de console. Ouve por novas solicitações e executa as ações do técnico (emitir orçamento, executar, finalizar, cancelar) no barramento.
* **`ClientApp` (Console)**:
    * **Localização**: `ClientApp/`
    * **Função**: Simula a lógica do aplicativo do cliente em um ambiente de console. Permite solicitar manutenção e receber notificações do andamento do serviço.

### 1.3. Interfaces de Frontend (Web - Flask)

São aplicações web baseadas em Flask (Python) com HTML/CSS/JavaScript simples para proporcionar uma interface gráfica de usuário para o cliente e o técnico.

* **`ClientFrontend`**:
    * **Localização**: `ClientFrontend/`
    * **Tecnologias**: Flask, HTML, CSS, JavaScript.
    * **Função**: Permite ao cliente solicitar manutenção através de uma interface web, digitar a descrição do problema e visualizar as notificações em tempo real, incluindo o valor do orçamento e opções para aprovar ou recusar.
* **`TechnicianFrontend`**:
    * **Localização**: `TechnicianFrontend/`
    * **Tecnologias**: Flask, HTML, CSS, JavaScript.
    * **Função**: Proporciona uma interface para o técnico visualizar as ordens de serviço ativas, emitir orçamentos (com campo de digitação livre e formatação), executar e finalizar serviços.

---

## 2. Fluxo de Comunicação Principal

1.  **Solicitação do Cliente**: O `ClientFrontend` ou `ClientApp` publica uma mensagem de `SOLICITAR_MANUTENCAO` no canal `initial_maintenance_requests`.
2.  **Criação da Ordem de Serviço**: O `ServiceOrderService` escuta `initial_maintenance_requests`, cria uma nova ordem de serviço em seu banco de dados e notifica outros serviços sobre a criação de um canal específico para o cliente (`maintenance_channel_<client_id>`).
3.  **Engajamento do Técnico**: O `TechnicianFrontend` ou `TechnicianApp` ouve `initial_maintenance_requests`, inicia um novo serviço, subscreve ao canal específico do cliente e emite um `MENSAGEM_ORCAMENTO` via esse canal.
4.  **Notificação ao Cliente**: O `MessagingService` recebe `MENSAGEM_ORCAMENTO`, extrai o valor e o cliente, e publica uma `NOTIFICACAO_ORCAMENTO` (incluindo o valor) de volta ao canal do cliente. O `ClientFrontend` e `ClientApp` exibem essa notificação.
5.  **Resposta do Cliente**: O `ClientFrontend` ou `ClientApp` permite ao cliente `APROVAR_ORCAMENTO` ou `NEGAR_ORCAMENTO` no canal específico.
6.  **Execução e Conclusão**: O `TechnicianFrontend` ou `TechnicianApp` prossegue com a `EXECUCAO_SERVICO` e, finalmente, envia uma `MENSAGEM_CONCLUSAO_SERVICO` ou `SERVICO_CANCELADO` no canal.
7.  **Fechamento do Canal**: O `ServiceOrderService` recebe a conclusão/cancelamento, atualiza o status final da OS, e publica uma mensagem `CHANNEL_CLOSED` no canal específico, sinalizando para todos os envolvidos que a comunicação para aquela OS foi encerrada.

---

## 3. Configuração e Instalação

### 3.1. Pré-requisitos

Para configurar e executar o sistema, você precisará dos seguintes itens:

* **Dispositivo Android**: Um smartphone com Android (versão 10 ou superior recomendada).
* **Aplicativo UserLAnd**: Instale o UserLAnd pela Google Play Store em seu dispositivo Android.
* **Python 3**: Instalado em sua(s) máquina(s) local(is) para executar os aplicativos do cliente, técnico e serviços. Python 3.10.12 ou superior é recomendado.
* **Conectividade de Rede**: Certifique-se de que seu dispositivo Android e todas as máquinas de aplicação estejam na mesma rede local.
* **Git**: Para clonar este repositório.

### 3.2. Configuração do Barramento de Serviços Android (Redis)

O barramento de serviços (Redis) será executado no seu dispositivo Android via UserLAnd.

1.  **Instalar UserLAnd**: Baixe e instale o UserLAnd em seu dispositivo Android. Abra-o e configure uma distribuição **Ubuntu`.
2.  **Acessar Terminal Ubuntu**: Uma vez que o Ubuntu estiver configurado no UserLAnd, abra seu terminal.
3.  **Atualizar e Fazer Upgrade**:
    ```bash
    sudo apt update
    sudo apt upgrade
    ```

4.  **Instalar Servidor Redis**:
    ```bash
    sudo apt install redis-server
    ```

5.  **Configurar Redis para Acesso Externo**: Edite o arquivo de configuração do Redis:
    ```bash
    sudo nano /etc/redis/redis.conf
    ```
    * Encontre a linha `bind 127.0.0.1 -::1` e altere-a para `bind 0.0.0.0`.
    * Encontre a linha `protected-mode yes` e altere-a para `protected-mode no`.
    * Salve e saia (Ctrl+O, Enter, Ctrl+X).
6.  **Iniciar Servidor Redis**: Você pode iniciar o Redis diretamente:
    ```bash
    redis-server /etc/redis/redis.conf
    ```
    *Mantenha este terminal aberto, pois o Redis precisa estar rodando constantemente.*
7.  **Encontrar Endereço IP do Dispositivo Android**: Em seu dispositivo Android (dentro do terminal do UserLAnd), execute:
    ```bash
    sudo apt install net-tools
    ifconfig
    ```
    Anote o endereço IP (ex: `192.168.1.7`). Este IP será usado por todos os outros serviços da aplicação para se conectar ao Redis. **Este IP será solicitado pelo script de inicialização.**

### 3.3. Configuração dos Serviços da Aplicação

1.  **Clonar o Repositório**: Em sua máquina local, clone o projeto:
    ```bash
    git clone [https://github.com/murilopoli/Sustainable-Messaging-System.git](https://github.com/murilopoli/Sustainable-Messaging-System.git)
    cd Sustainable-Messaging-System
    ```

2.  **Instalar Dependências Python**: Para cada pasta de serviço/frontend (`ClientApp`, `TechnicianApp`, `MessagingService`, `ServiceOrderService`, `ClientFrontend`, `TechnicianFrontend`), você precisará instalar as dependências. O script abaixo faz isso para todas as pastas. Execute na raiz do projeto:
    ```bash
    pip install -r ClientApp/requirements.txt
    pip install -r TechnicianApp/requirements.txt
    pip install -r MessagingService/requirements.txt
    pip install -r ServiceOrderService/requirements.txt
    # Para os frontends Flask:
    pip install Flask redis
    ```

3.  **Configurar Host Redis Automaticamente**: O script `start_all_services.sh` (próxima seção) irá configurar o `REDIS_HOST` em todos os arquivos Python automaticamente para você.

---

## 4. Execução do Sistema

Certifique-se de que o Barramento de Serviços Android (broker Redis) esteja em execução em seu dispositivo Android primeiro (Passo 3.2.6).

### 4.1. Usando o Script de Inicialização Automatizada

Para simplificar a execução de todos os serviços e frontends, um script shell chamado `start_all_services.sh` já está localizado na **raiz** do seu projeto (`Sustainable-Messaging-System/`). Este script automatiza as seguintes tarefas:

* Solicita o IP do host Redis ao usuário.
* Configura automaticamente o `REDIS_HOST` em todos os 6 arquivos Python de serviço e frontend.
* Inicia todos os serviços de backend e frontends Flask em segundo plano, redirecionando suas saídas para arquivos de log individuais dentro de subpastas `logs/` de cada serviço.

**Passos para Executar o Script:**

1.  **Dê permissão de execução (se ainda não o fez):** Abra seu terminal, navegue até a pasta raiz do projeto e execute:
    ```bash
    chmod +x start_all_services.sh
    ```
2.  **Execute o script:**
    ```bash
    ./start_all_services.sh
    ```
3.  O script pedirá para você **digitar o IP do host Redis**. Insira o IP do seu dispositivo Android (obtido no Passo 3.2.7). Se o Redis estiver rodando localmente na sua máquina para testes (não recomendado para o fluxo completo com Android), você pode digitar `localhost`.
4.  Acompanhe a saída do script. Ele informará se a configuração de IP foi bem-sucedida para cada arquivo e se os serviços estão sendo iniciados. Eles rodarão em segundo plano.

### 4.2. Acessando as Interfaces e Testando o Fluxo

1.  **Interface do Cliente**: Abra seu navegador e vá para `http://localhost:5000`.
2.  **Interface do Técnico**: Abra outra aba ou janela do navegador e vá para `http://localhost:5001`.

**Siga o Fluxo de Manutenção:**

1.  **No Cliente (`http://localhost:5000`):**
    * No campo "Descreva o problema", digite a descrição de uma manutenção (ex: "Vazamento na torneira").
    * Clique em "Solicitar Manutenção".
    * Observe a seção "Notificações" para ver as mensagens de andamento.

2.  **No Técnico (`http://localhost:5001`):**
    * Uma nova "Ordem de Serviço" deve aparecer listada para o cliente que fez a solicitação.
    * O status será `new`.
    * No campo "Valor do Orçamento", digite o valor (ex: `150.75`). O campo deve aceitar a digitação livremente e formatar.
    * Clique em "Emitir Orçamento".
    * O status da OS será `quote sent`.

3.  **De volta ao Cliente (`http://localhost:5000`):**
    * Uma nova notificação aparecerá, informando o valor do orçamento (ex: "Notificação de orçamento recebida: R$ 150.75. Aprovar ou recusar?").
    * Os botões "Aprovar Orçamento" e "Negar Orçamento" devem aparecer.
    * Clique em "Aprovar Orçamento".

4.  **De volta ao Técnico (`http://localhost:5001`):**
    * O status da OS será `orcamento aprovado`.
    * Clique em "Executar Serviço".
    * Aguarde alguns segundos e clique em "Finalizar Serviço".
    * O status da OS mudará para `completed` e, em breve, a OS desaparecerá da lista do técnico.

5.  **No Cliente (`http://localhost:5000`):**
    * Uma notificação final de "Serviço concluído! Obrigado!" aparecerá, e os botões desaparecerão.

---

## 5. Resolução de Problemas

* **Problemas de Conexão (`TimeoutError`)**:
    * Verifique se o Redis está rodando no seu dispositivo Android.
    * Confirme o IP do Android e certifique-se de que ele foi digitado corretamente ao executar `start_all_services.sh`.
    * Verifique a configuração do Redis (`bind 0.0.0.0` e `protected-mode no`).
    * Certifique-se de que não há firewalls bloqueando a porta `6379` entre a sua máquina e o Android. Faça um `ping` do seu terminal para o IP do Android.
* **Interfaces não atualizam ou perdem estado (ex: campo de input esvazia)**:
    * O script `start_all_services.sh` já configura `debug=False` e `use_reloader=False` para os frontends Flask. Se você estiver executando manualmente, certifique-se de usar essas opções para evitar o reset de estado em memória.
* **Serviços não iniciam ou param inesperadamente**:
    * Verifique os logs de cada serviço em suas pastas `logs/` (ex: `Sustainable-Messaging-System-main/ServiceOrderService/logs/ServiceOrderService.log`) para mensagens de erro específicas.
* **Problemas de Permissão**:
    * Certifique-se de que o script `start_all_services.sh` tem permissão de execução (`chmod +x`).
