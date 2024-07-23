import os.path
import re
import socket
import sys
from subprocess import PIPE, Popen
from urllib.parse import urljoin

BASEDIR = os.path.abspath(os.path.dirname(__file__))


def get_ephemeral_port():
    # Somehow getting random high port doesn't work on pypy
    if re.search("PyPy", sys.version):
        return str(9112)
    s = socket.socket()
    s.bind(("", 0))
    return str(s.getsockname()[1])


class MockScrapydServer:
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password

    def __enter__(self):
        self.http_port = get_ephemeral_port()
        command = [sys.executable, os.path.join(BASEDIR, "mockapp.py"), self.http_port]
        if self.username and self.password:
            command.extend([f"--username={self.username}", f"--password={self.password}"])

        self.process = Popen(command, stdout=PIPE)

        # The loop is expected to run 3 times.
        # 2001-02-03 04:05:06-0000 [-] Log opened.
        # 2001-02-03 04:05:06-0000 [-] Basic authentication disabled as either `username` or `password` is unset
        # 2001-02-03 04:05:06-0000 [-] Scrapyd web console available at http://127.0.0.1:53532/
        self.head = []
        for _ in range(10):
            line = self.process.stdout.readline()
            self.head.append(line)
            if address := re.search("available at (.+/)", line.decode()):
                self.url = address.group(1)
                break

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.process.terminate()
        self.stdout, _ = self.process.communicate()
        self.stdout = b"".join(self.head) + self.stdout

    def urljoin(self, path):
        return urljoin(self.url, path)


if __name__ == "__main__":
    with MockScrapydServer() as server:
        while True:
            pass
