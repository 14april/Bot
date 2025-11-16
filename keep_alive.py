import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class PingServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive")

def run_server():
    # Railway dùng biến PORT, không phải 10000
    port = int(os.getenv("PORT", 10000)) 
    server = HTTPServer(("0.0.0.0", port), PingServer)
    print(f"Server ping đang chạy trên port {port}...")
    server.serve_forever()

def start_keep_alive():
    """Chạy server trong một thread riêng biệt."""
    threading.Thread(target=run_server, daemon=True).start()
