FROM python:3
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
ADD requirements/common.pip /code/
RUN pip install -r common.pip --src /usr/local/src
RUN pip install gunicorn==19.9.0 --src /usr/local/src
ADD . /code/

# expose the port 8000
EXPOSE 8000
