# materia_mongodb

Projeto de estudo de banco de dados não relacional com MongoDB, incluindo:
- Estrutura de coleções e dados de exemplo (dump em `base_completa/map_app_db`)
- Passo a passo para restaurar o banco com `mongorestore`
- Comandos para verificar o status e integridade do banco
- Dashboard em Streamlit (`dashboard.py`) para visualizar dados e métricas

## Visão Geral
- **Objetivo:** Demonstrar modelagem, carga e visualização de dados em MongoDB para uma aplicação de mapeamento local.
- **Stack:** MongoDB, Python (Streamlit), scripts auxiliares (`create_db.ipynb`, `pop_db.py`).
- **Dump incluído:** Coleções exportadas via `mongodump` em `base_completa/map_app_db`.

## Estrutura do Banco (Dump)
Os arquivos de dump no diretório `base_completa/map_app_db` contêm as seguintes coleções:
- **`users` / `users+`:** usuários e informações adicionais.
- **`residences`:** residências associadas aos usuários/área do mapa.
- **`objects`:** objetos/entidades georreferenciadas.
- **`scans`:** registros de varreduras/coletas no mapa.
- **`history`:** histórico de eventos/alterações.

Cada coleção possui arquivos `.bson` e `.metadata.json` (schema e índices quando aplicável). O arquivo `prelude.json` guarda metadados gerados pelo processo de dump.

## Pré-requisitos
- **Linguagem:** Todo o projeto foi feito em **Python**. Certifique-se de ter **Python 3.10+** e o **pip** instalados na sua máquina.
- **MongoDB Community ou Atlas:** Ter um servidor MongoDB local (Windows) ou uma instância Atlas.
- **Ferramentas de database:** `mongorestore` (MongoDB Database Tools).
- **Dependências Python:** listadas em `requirements.txt` e instaladas via `pip`.

> Importante: Para conexões com o Atlas, adicione seu IP atual à allowlist do cluster (Network Access) antes de conectar/restaurar.

## Instalação de Dependências (Python)
No diretório do projeto, instale todas as bibliotecas necessárias usando o `requirements.txt`:
```powershell
Set-Location "c:\Users\seu_usuario\Desktop\..\conteudo_do_repositorio";
python -m pip install --upgrade pip;
pip install -r .\requirements.txt
```

## Restaurar o Banco com `mongorestore`
A restauração irá criar/popular o banco a partir do dump já presente no repositório.

1) Abra o PowerShell e navegue até a pasta do projeto:
```powershell
Set-Location "c:\Users\seu_usuario\Desktop\..\conteudo_do_repositorio"
```

2) Verifique se o serviço MongoDB está rodando (local):
```powershell
Get-Service | Where-Object {$_.Name -like "*MongoDB*"}
```
Se não estiver em execução e você usa serviço local, inicie-o:
```powershell
Start-Service -Name "MongoDB"
```
> Se estiver utilizando o Atlas: certifique-se de que seu IP está permitido no cluster e tenha a sua `STRING_DE_CONEXAO` em mãos.

3) Execute o `mongorestore` apontando para o diretório do dump. O nome do banco será inferido dos metadados; você pode forçar com `--db` se preferir.
```powershell
mongorestore --drop --dir "base_completa\map_app_db"
```
- **`--drop`:** Apaga coleções existentes antes de restaurar (evita duplicações).
- Para restaurar em um banco específico, por exemplo `map_app_db`:
```powershell
mongorestore --drop --db map_app_db --dir "base_completa\map_app_db"
```
- Para um servidor remoto (Atlas), use o formato recomendado:
```powershell
mongorestore --uri="STRING_DE_CONEXAO" --db NOME_DO_BANCO caminho_para_banco_bson
```
Exemplo:
```powershell
mongorestore --uri="mongodb+srv://USUARIO:SENHA@CLUSTER.mongodb.net/?retryWrites=true&w=majority" --db map_app_db base_completa\map_app_db
```

Observação: se o dump foi criado com `mongodump --db map_app_db`, `mongorestore` detectará o nome do banco. Caso contrário, especifique `--db`.

## Verificar Status e Conteúdo do Banco (via Python)
Você pode verificar as coleções e contagens usando Python com `pymongo`.

Crie um arquivo `check_db.py` com o conteúdo abaixo ou execute em um notebook Python:
```python
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
db_name = os.getenv("MONGODB_DB", "map_app_db")

client = MongoClient(uri)
db = client[db_name]

collections = db.list_collection_names()
print("Coleções:", collections)

def count(col):
	try:
		return db[col].count_documents({})
	except Exception as e:
		print(f"Erro ao contar {col}:", e)
		return None

for col in ["users", "users+", "residences", "objects", "scans", "history"]:
	print(col, count(col))

print("Exemplos de documentos em users:")
for doc in db["users"].find().limit(5):
	print(doc)
```

## Scripts Auxiliares
- `create_db.ipynb`: notebook para experimentos de criação/estrutura do banco.
- `pop_db.py`: script de popular dados (se desejar gerar/alterar dados localmente). Execute apenas se precisar, pois o dump já contém dados prontos.

## Dashboard em Streamlit (`dashboard.py`)
O dashboard permite visualizar dados e métricas do banco em uma interface web simples.

### Configuração (.env)
- Duplique o arquivo `.env.example` para `.env` e ajuste as variáveis:
```
MONGODB_URI=STRING_DE_CONEXAO
MONGODB_DB=map_app_db
```
- Em Atlas, lembre de adicionar seu IP na allowlist do cluster antes de iniciar o app.

### Instalação de dependências
Se você ainda não tem Streamlit e drivers instalados, execute:
```powershell
python -m pip install --upgrade pip
pip install -r .\requirements.txt
```

### Executar o dashboard
No diretório do projeto, rode:
```powershell
streamlit run .\dashboard.py
```
Após iniciar, o Streamlit abrirá no navegador (geralmente `http://localhost:8501`).

### Funcionalidades esperadas
- Visualização de coleções, contagens e amostras de registros.
- Filtros básicos de consulta.
- Indicadores simples (por exemplo, número de usuários, objetos e scans).

## Dicas de Troubleshooting
- **`mongorestore` não encontrado:** Instale MongoDB Database Tools ou certifique-se de que o binário esteja no `PATH`.
- **Permissões/serviço:** Verifique se o serviço MongoDB está ativo no Windows (`Get-Service`, `Start-Service`).
- **Conexão Atlas:** Confira IP allowlist e credenciais no cluster.
- **Coleção `users+`:** Em `mongosh`, use `db["users+"]` para acessar coleções com caracteres especiais.

## Descrição do Projeto (resumo do PDF)
- Este repositório inclui o documento `desc_projeto.pdf` presente dentro da pasta `sobre_o_projeto` com a descrição detalhada do contexto, objetivos e etc. 
