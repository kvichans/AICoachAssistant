FROM python:3.10-slim

WORKDIR /usr/src/app/

COPY . /usr/src/app/

RUN apt-get update

RUN pip install -r bot_requirements.txt

CMD ["python", "main.py"]