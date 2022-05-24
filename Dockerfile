FROM python

# Updating image os
RUN apt-get update && apt-get upgrade -y 
RUN apt-get install vim -y 

# Install pip depend

# Install scrapyd
COPY . /scrapyd-install
WORKDIR /scrapyd-install
RUN pip install -r requirements.txt
RUN python setup.py install

# Copy conf file to /etc/scrapyd/
WORKDIR /
ADD ./config-files/scrapyd.conf /etc/scrapyd/

EXPOSE 6800


# Run logparser
WORKDIR /var/lib/scrapyd/
CMD ["sh", "-c", "( logparser -dir /etc/scrapyd/logs & ) && scrapyd --pidfile="]
