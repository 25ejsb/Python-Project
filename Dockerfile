FROM python:3.10
# RUN mkdir /
COPY . .
WORKDIR .
RUN pip install -r requirements.txt