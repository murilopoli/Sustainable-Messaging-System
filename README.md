# Sistema de Mensagens Sustentável - Barramento de Serviços Android

Este projeto implementa um sistema de mensageria que utiliza um Barramento de Serviços (Service Bus) em um dispositivo Android, simulando o fluxo de uma solicitação de manutenção desde o cliente até a finalização do serviço pelo técnico.

---

## 1. Configuração e Instalação

### 1.1. Pré-requisitos

Para configurar e executar o sistema, você precisará dos seguintes itens:

* **Dispositivo Android**: Um smartphone com Android (versão 10 ou superior recomendada).
* **Aplicativo UserLAnd**: Instale o UserLAnd pela Google Play Store em seu dispositivo Android.
* **Python 3**: Instalado em sua(s) máquina(s) local(is) para executar os aplicativos do cliente, técnico e serviços. Python 3.10.12 ou superior é recomendado.
* **Conectividade de Rede**: Certifique-se de que seu dispositivo Android e todas as máquinas de aplicação estejam na mesma rede local.
* **Git**: Para clonar este repositório.

### 1.2. Configuração do Barramento de Serviços Android

O barramento de serviços (Redis) será executado no seu dispositivo Android via UserLAnd.

1.  **Instalar UserLAnd**: Baixe e instale o UserLAnd em seu dispositivo Android. Abra-o e configure uma distribuição **Ubuntu**.
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
7.  **Encontrar Endereço IP do Dispositivo Android**: Em seu dispositivo Android (dentro do terminal do UserLAnd), execute:
    ```bash
    sudo apt install net-tools
    ifconfig
    ```
    Anote o endereço IP (ex: `192.168.1.7`). Este IP será usado por todos os outros serviços da aplicação para se conectar ao Redis.

### 1.3. Configuração dos Serviços da Aplicação

Para cada serviço da aplicação (**ClientApp**, **TechnicianApp**, **MessagingService**, **ServiceOrderService**):

1.  **Clonar o Repositório**:
    ```bash
    git clone https://github.com/murilopoli/Sustainable-Messaging-System.git
    cd Sustainable-Messaging-System
    ```
    
2.  **Navegar para o Diretório do Serviço**:
    ```bash
    cd ClientApp # ou TechnicianApp, MessagingService, ServiceOrderService
    ```
3.  **Instalar Dependências Python**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configurar Host Redis**: Abra o arquivo Python principal de cada serviço (`client_interface.py`, `technician_interface.py`, `messaging_consumer.py`, `service_order_consumer.py`) e substitua `[ANDROID_DEVICE_IP]` pelo endereço IP real do seu dispositivo Android, anotado na etapa 7 da Configuração do Barramento de Serviços Android. A porta será `6379`.

---

## 2. Execução

Certifique-se de que o Barramento de Serviços Android (broker Redis) esteja em execução em seu dispositivo Android primeiro.

### Iniciar Serviços (em terminais separados em diferentes máquinas ou abas):

* **Serviço de Ordem de Serviço**: (Este serviço gerencia o banco de dados de ordens de serviço)
    ```bash
    cd ServiceOrderService
    python service_order_consumer.py
    ```
* **Serviço de Mensageria**: (Este serviço lida com as notificações do cliente)
    ```bash
    cd MessagingService
    python messaging_consumer.py
    ```
* **Aplicação do Técnico**: (Simula a interface do técnico)
    ```bash
    cd TechnicianApp
    python technician_interface.py
    ```
* **Aplicação do Cliente**: (Simula as ações do cliente)
    ```bash
    cd ClientApp
    python client_interface.py
    ```

### Siga o Fluxo:

1.  No terminal do **ClientApp**, digite uma mensagem para "Solicitar manutenção".
2.  Observe a saída nos terminais do **TechnicianApp**, **MessagingService** e **ServiceOrderService** à medida que o processo se desenrola.
3.  O **TechnicianApp** solicitará ações (por exemplo, "Emitir orçamento", "Aprovar orçamento", "Executar serviço", "Finalizar serviço"). Siga as instruções para guiar a solicitação de serviço ao longo de seu ciclo de vida.
4.  Cada nova solicitação de serviço iniciada pelo técnico criará um canal exclusivo e, após a finalização do serviço, o sistema sinalizará para fechar aquele canal específico.
