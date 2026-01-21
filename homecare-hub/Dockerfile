FROM python:3.12-bullseye

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

WORKDIR /app/

COPY . /app/

EXPOSE 9000

ENTRYPOINT ["streamlit", "run", "Home.py", " --server.address", "0.0.0.0", "--server.port", "9000"]
