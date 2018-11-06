# python:alpine is 3.{latest}
FROM jfloff/alpine-python:3.6

RUN pip3 install gevent==1.3.4 flask==1.0.2 gunicorn==19.9.0 requests==2.19.1

COPY src /src/

WORKDIR /src

EXPOSE 6604

ENTRYPOINT ["gunicorn", "-w 4", "-b :6604", "-k gevent", "-t 180", "app:app"]
