FROM httpd:2.4
RUN apt update && apt install -y libapache2-mod-wsgi-py3
COPY samm.conf /usr/local/apache2/conf/extra
COPY apache.py /usr/local/samm/scripts/apache.py
RUN echo "Include /usr/local/apache2/conf/extra/samm.conf" >> /usr/local/apache2/conf/httpd.conf
