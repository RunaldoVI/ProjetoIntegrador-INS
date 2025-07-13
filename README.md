# ProjetoIntegrador-INS
Passo 1 - Criar um ambiente virtual:
Linux/macOS:
python3 -m venv venv

Windows:
python -m venv venv

Passo 2 - Ativar o ambiente Virtual:
Linux/macOS:
source venv/bin/activate

Windows (CMD):
venv\Scripts\activate

Windows (PowerShell):
.\venv\Scripts\Activate.ps1


Passo 3 - Instalar as dependências:
pip install -r requirements.txt

Passo 4 - Aceder ao site para instalar o Ollama:
https://ollama.com/

Passo 5 - Instalar o model Mistral:7b
Abrir o cmd, correr a seguinte linha:
ollama run mistral
Deixar a instalar os 4.4gb 

Passo 6 - Correr o projeto:
python ProjetoFinal.py

