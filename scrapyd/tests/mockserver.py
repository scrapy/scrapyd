import os
import re
import shutil
import socket
import sys
from subprocess import PIPE, Popen
from urllib.parse import urljoin


def get_ephemeral_port():
    # Somehow getting random high port doesn't work on pypy
    if re.search("PyPy", sys.version):
        return str(9112)
    s = socket.socket()
    s.bind(("", 0))
    return str(s.getsockname()[1])


class MockScrapyDServer:
    def __init__(self, authentication=None):
        self.authentication = authentication

    def __enter__(self, authentication=None):
        """Launch ScrapyD application object with ephemeral port
        """
        command = [
            sys.executable, '-m',
            "scrapyd.tests.start_mock_app",
            get_ephemeral_port()
        ]
        if self.authentication is not None:
            command.append('--auth=' + self.authentication)

        self.proc = Popen(command, stdout=PIPE)
        for x in range(10):
            msg = self.proc.stdout.readline().strip().decode("ascii")
            addr_line = re.search("available at (.+/)", msg)
            if addr_line:
                self.url = addr_line.group(1)
                break

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.proc.kill()
        self.proc.communicate()
        # TODO create eggs in temporary directory
        if os.path.isdir("eggs") and os.listdir("eggs") != []:
            shutil.rmtree("eggs")

    def urljoin(self, path):
        return urljoin(self.url, path)


if __name__ == "__main__":
    with MockScrapyDServer() as server:
        print(f"Listening at {server.url}")
        while True:
            pass
