FROM python:3.11

WORKDIR /app

COPY app/ /app/
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.org/simple --timeout=100

CMD ["python", "ProjetoFinal.py"]
