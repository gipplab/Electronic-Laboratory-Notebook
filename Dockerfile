FROM python:3
ENV PYTHONUNBUFFERED=1
WORKDIR /code
ADD ./01_Data ./code/Data/01_Data
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY . /code/

