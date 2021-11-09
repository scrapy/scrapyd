import re
import socket
from pathlib import Path
from subprocess import Popen, PIPE
from urllib.parse import urljoin


def get_ephemeral_port():
    # TODO pass port to scrapyd
    s = socket.socket()
    s.bind(("", 0))
    return s.getsockname()[1]


class MockScrapyDServer:
    def __enter__(self):
        cwd = str(Path(__file__).absolute().parent.parent)
        command = ["twistd", "-y", "txapp.py", "-on"]
        self.proc = Popen(command, stdout=PIPE, cwd=cwd)
        for x in range(5):
            msg = self.proc.stdout.readline().strip().decode("ascii")
            if addr_line := re.search("available at (.+/)", msg):
                self.url = addr_line.group(1)
                break

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.proc.kill()
        self.proc.communicate()

    def urljoin(self, path):
        return urljoin(self.url, path)


if __name__ == "__main__":
    with MockScrapyDServer() as server:
        print(f"Listening at {server.url}")
        while True:
            pass