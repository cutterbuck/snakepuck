import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


port = int(os.environ.get("PORT", 8000))
print(f"Starting healthcheck server on port {port}", flush=True)
HTTPServer(("0.0.0.0", port), Handler).serve_forever()
