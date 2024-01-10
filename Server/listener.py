from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib import parse
import sys
import json

IP = "10.2.40.81"

class RequestHandler(BaseHTTPRequestHandler):
    
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        data = self.rfile.read(length).decode()
        data_dict = parse.parse_qs(data)
        print(f"Recieved message: {data_dict['message'][0]}")

        self.send_response(200)
        
        self.send_header("Content-type","application/json")
        self.end_headers()

        self.wfile.write(json.dumps({"message" : f"Message recieved: {data_dict['message'][0]}"}).encode())


def main(argc: int, argv: list[str]) -> int:
    server = ThreadingHTTPServer((IP,1337),RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("So long!")
    return 0

if __name__ == "__main__":
    sys.exit(main(len(sys.argv),sys.argv))