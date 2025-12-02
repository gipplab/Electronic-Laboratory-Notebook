FROM python:3.7
RUN apt-get update && apt-get install --yes --no-install-recommends libgl1 curl && apt-get clean && rm -rf /var/lib/apt/lists/*
ENV PYTHONUNBUFFERED=1
WORKDIR /code
ADD ./01_Data ./code/Data/01_Data
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY . /code/