import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from healthtech_service import AppointmentQuestion, InfraiClient, answer_question


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/answer":
            self.send_error(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        collection = payload.pop("collection", "healthtech-docs")
        request = AppointmentQuestion(**payload)
        result = answer_question(request, InfraiClient(), collection)
        body = json.dumps(result.__dict__).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
