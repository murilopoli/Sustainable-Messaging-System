#!/bin/bash

# Este script inicia todos os serviços do Sustainable Messaging System.
# Ele também configura o REDIS_HOST em todos os arquivos Python automaticamente.

echo "--- Iniciando todos os serviços do Sustainable Messaging System ---"
echo "------------------------------------------------------------------"

# --- Configurar REDIS_HOST nos arquivos Python ---

read -p "Digite o IP do host Redis (ex: 192.168.1.100 ou localhost se estiver na mesma máquina): " REDIS_HOST_INPUT

# Lista de arquivos Python que precisam ter o REDIS_HOST configurado
PYTHON_FILES=(
    "ClientApp/client_interface.py"
    "TechnicianApp/technician_interface.py"
    "MessagingService/messaging_consumer.py"
    "ServiceOrderService/service_order_consumer.py"
    "ClientFrontend/app.py"
    "TechnicianFrontend/app.py"
)

# Obtém o diretório deste script e muda para ele
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo ""
echo "Configurando REDIS_HOST para '$REDIS_HOST_INPUT' em todos os arquivos Python..."

# Detecta o sistema operacional para compatibilidade com 'sed'
SED_INPLACE_OPT=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS 'sed' requires an argument for -i (e.g., -i '')
    SED_INPLACE_OPT="''"
fi

for file in "${PYTHON_FILES[@]}"; do
    FILE_PATH="$SCRIPT_DIR/$file"
    if [ -f "$FILE_PATH" ]; then
        # Usa 'eval' para lidar corretamente com a opção -i do sed em diferentes OS
        # O delimitador '|' é usado em 'sed' porque o IP pode conter '.'
        eval "sed -i $SED_INPLACE_OPT \"s|REDIS_HOST = '.*'|REDIS_HOST = '$REDIS_HOST_INPUT'|g\" \"$FILE_PATH\""
        if [ $? -eq 0 ]; then
            echo " - '$file': REDIS_HOST configurado com sucesso."
        else
            echo " - ERRO: Falha ao configurar REDIS_HOST em '$file'."
        fi
    else
        echo " - AVISO: Arquivo não encontrado: '$file'. Pulando a configuração."
    fi
done

echo "Configuração de REDIS_HOST concluída."

# --- Relembre o usuário sobre o Redis no Android ---
echo ""
echo "--- Lembrete Importante: ---"
echo "Certifique-se de que o servidor Redis esteja rodando no seu dispositivo Android!"
echo "------------------------------"

# Função para iniciar um serviço em segundo plano
start_service() {
    local dir=$1
    local script=$2
    local name=$3
    echo "Iniciando $name..."
    mkdir -p "$dir/logs" # Garante que a pasta de logs existe
    nohup python3 "$dir/$script" > "$dir/logs/$name.log" 2>&1 &
    echo "[$name] Iniciado. Saída redirecionada para $dir/logs/$name.log (PID $!)"
    sleep 2 # Dá um tempo para o serviço inicializar
}

# --- Iniciar serviços de Backend ---
echo ""
echo "Iniciando serviços de Backend..."
start_service "ServiceOrderService" "service_order_consumer.py" "ServiceOrderService"
start_service "MessagingService" "messaging_consumer.py" "MessagingService"
start_service "TechnicianApp" "technician_interface.py" "TechnicianApp"
start_service "ClientApp" "client_interface.py" "ClientApp"

# --- Iniciar Frontends Flask ---
echo ""
echo "Iniciando Frontends Flask..."
start_service "TechnicianFrontend" "app.py" "TechnicianFrontend"
start_service "ClientFrontend" "app.py" "ClientFrontend"

echo ""
echo "------------------------------------------------------------------"
echo "Todos os serviços foram iniciados em segundo plano."
echo "Para verificar os logs de cada serviço, consulte os arquivos em suas respectivas pastas 'logs/'."
echo "Exemplo: tail -f Sustainable-Messaging-System-main/ServiceOrderService/logs/ServiceOrderService.log"
echo ""
echo "Acesse as interfaces no seu navegador:"
echo "Interface do Cliente: http://localhost:5000"
echo "Interface do Técnico: http://localhost:5001"
echo "------------------------------------------------------------------"
echo "Pressione Ctrl+C para sair deste script, mas os serviços continuarão rodando."
echo "Para parar todos os serviços, use 'killall python3' (cuidado, isso mata todos os processos python)."
echo "Ou identifique os PIDs usando 'ps aux | grep python3' e use 'kill <PID>'."
echo "Aguarde alguns segundos para que todos os serviços se estabilizem."
echo ""