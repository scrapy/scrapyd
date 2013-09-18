#!/bin/bash

source /etc/bash_completion.d/virtualenvwrapper
workon scrapyd
python /home/ubuntu/.virtualenvs/scrapyd/bin/twistd -ny extras/scrapyd.tac
