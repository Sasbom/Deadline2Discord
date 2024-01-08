from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse
import sys

IP = "10.2.40.81"

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        data = self.rfile.read(length).decode()
        data_dict = parse.parse_qs(data)
        print(f"Recieved message: {data_dict}")

        self.send_response(200)
        self.end_headers()


def main(argc: int, argv: list[str]) -> int:
    server = HTTPServer((IP,1337),RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("So long!")
    return 0

if __name__ == "__main__":
    sys.exit(main(len(sys.argv),sys.argv))