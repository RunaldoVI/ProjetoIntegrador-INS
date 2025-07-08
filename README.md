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

Passo 4 - Aceder ao site para instalar o ficheiro GloVE:
https://nlp.stanford.edu/projects/glove/

Passo 5 - Instalar o glove.6B.zip
Após a instalação do glove.6b.zip, descomprimir o zip e mover o ficheiro glove.6b.100d.txt para a pasta glove do projeto.

Passo 6 - Correr o projeto:
python ProjetoFinal.py

