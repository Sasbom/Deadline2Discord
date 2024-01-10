import sys
from urllib import request, parse
import asyncio
import json

IP = "10.2.40.81"

async def log_to_server(message):
    _adress = f"http://{IP}:1337"
    _dict = {"message" : message}
    _data = parse.urlencode(_dict).encode()
    _request = request.Request(_adress, data=_data, method="POST")
    try:
        data = None
        with request.urlopen(_request) as response:
            response_data = response.read().decode('utf-8')
        if response_data:
            return json.loads(response_data)["message"]

    except:
        print("it ain't workin' chief")


def main(argc: int, argv: list[str]) -> int:
    mainloop = asyncio.get_event_loop()
    
    results = mainloop.run_until_complete(asyncio.wait([
        log_to_server("test message"),
        log_to_server("test message 2")
    ]))

    print([r.result() for r in results[0]])
    
    
if __name__ == "__main__":
    sys.exit(main(len(sys.argv),sys.argv))