import os 
import sys
import json
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

CONFIG_FILE = "servers.json"
proxy_running = False
sock_proxy = None
http_server = None

def load_servers():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: pass
    return [{"name": "CubeCraft", "ip": "play.cubecraft.net", "port": 19132}]

def save_servers(servers):
    with open(CONFIG_FILE, "w") as f:
        json.dump(servers, f)

servers_list = load_servers()
active_server = servers_list[0] if servers_list else {"name": "None", "ip": "", "port": 19132}

def run_udp_proxy():
    global proxy_running, sock_proxy, active_server
    sock_proxy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock_proxy.bind(("0.0.0.0", 19132))
    except Exception as e:
        print(f"Fehler beim Binden von Port 19132: {e}")
        proxy_running = False
        return

    clients = {}
    while proxy_running:
        try:
            sock_proxy.settimeout(1.0)
            data, addr = sock_proxy.recvfrom(4096)
            
            if data.startswith(b'\x01'):
                pong = b'\x1c' + data[1:9] + b'\x00\x00\x00\x00\x00\x00\x00\x00'
                pong += b'\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x12\x34\x56\x78'
                motd = f"MCPE;{active_server['name']};589;1.20.0;0;10;123456789;World;Creative;1;19132;19132;".encode('utf-8')
                pong += len(motd).to_bytes(2, 'big') + motd
                sock_proxy.sendto(pong, addr)
                continue

            try:
                target_ip = socket.gethostbyname(active_server["ip"])
            except:
                target_ip = active_server["ip"]

            if addr not in clients:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                clients[addr] = s
                def forward():
                    while proxy_running:
                        try:
                            s.settimeout(1.0)
                            res, _ = s.recvfrom(4096)
                            sock_proxy.sendto(res, addr)
                        except:
                            if not proxy_running: break
                threading.Thread(target=forward, daemon=True).start()

            clients[addr].sendto(data, (target_ip, int(active_server["port"])))
        except socket.timeout:
            continue
        except Exception:
            break

HTML_CONTENT = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bedrock Proxy</title>
    <style>
        :root { --bg: #0f111a; --card: #181b28; --accent: #00e676; --danger: #ff5252; --text: #e1e6ed; --border: #23283b; }
        body { font-family: sans-serif; background: var(--bg); color: var(--text); padding: 20px; margin: 0; }
        .container { max-width: 500px; margin: 0 auto; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        h3 { color: var(--accent); margin-top: 0; }
        input, select, button { width: 100%; padding: 12px; margin-top: 8px; border-radius: 8px; border: 1px solid var(--border); background: #0f111a; color: #fff; font-size: 1rem; box-sizing: border-box; }
        button { background: var(--accent); color: #000; font-weight: bold; cursor: pointer; border: none; }
        .btn-stop { background: var(--danger); color: #fff; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Bedrock Console Proxy</h2>
        <div class="card">
            <h3>Server Auswählen</h3>
            <select id="serverSelect" onchange="selectServer()"></select>
            <br><br>
            <button id="toggleBtn" onclick="toggleProxy()">Proxy Starten</button>
        </div>
        <div class="card">
            <h3>Neuen Server Hinzufügen</h3>
            <input type="text" id="newName" placeholder="Server Name">
            <input type="text" id="newIp" placeholder="IP / Domain">
            <input type="number" id="newPort" value="19132" placeholder="Port">
            <button onclick="addServer()" style="margin-top:12px;">Speichern</button>
        </div>
    </div>
    <script>
        let isRunning = false;
        function loadServers() {
            fetch('/api/servers').then(r => r.json()).then(data => {
                const sel = document.getElementById('serverSelect');
                sel.innerHTML = '';
                data.servers.forEach((s, i) => {
                    sel.innerHTML += `<option value="${i}">${s.name} (${s.ip}:${s.port})</option>`;
                });
            }).catch(() => setTimeout(loadServers, 1000));
        }
        function selectServer() {
            const idx = document.getElementById('serverSelect').value;
            fetch('/api/select', { method: 'POST', body: JSON.stringify({ index: idx }) });
        }
        function addServer() {
            const name = document.getElementById('newName').value;
            const ip = document.getElementById('newIp').value;
            const port = document.getElementById('newPort').value;
            if(!name || !ip) return alert("Bitte Name und IP ausfüllen!");
            fetch('/api/add', { method: 'POST', body: JSON.stringify({ name, ip, port }) }).then(() => {
                document.getElementById('newName').value = '';
                document.getElementById('newIp').value = '';
                loadServers();
            });
        }
        function toggleProxy() {
            fetch('/api/toggle', { method: 'POST' }).then(r => r.json()).then(d => {
                isRunning = d.running;
                const btn = document.getElementById('toggleBtn');
                btn.innerText = isRunning ? "Proxy Stoppen" : "Proxy Starten";
                btn.className = isRunning ? "btn-stop" : "";
            });
        }
        window.onload = loadServers;
        setInterval(loadServers, 5000);
    </script>
</body>
</html>"""

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return
    def do_GET(self):
        if self.path == "/api/servers":
            self.send_response(200); self.send_header("Content-type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"servers": servers_list}).encode())
        else:
            self.send_response(200); self.send_header("Content-type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))

    def do_POST(self):
        global proxy_running, sock_proxy, active_server, servers_list
        length = int(self.headers.get('content-length', 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        
        if self.path == "/api/select":
            active_server = servers_list[int(body["index"])]
        elif self.path == "/api/add":
            servers_list.append({"name": body["name"], "ip": body["ip"], "port": body["port"]})
            save_servers(servers_list)
        elif self.path == "/api/toggle":
            proxy_running = not proxy_running
            if proxy_running: threading.Thread(target=run_udp_proxy, daemon=True).start()
            elif sock_proxy: sock_proxy.close()

        self.send_response(200); self.send_header("Content-type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps({"running": proxy_running}).encode())

def start_server():
    global http_server
    http_server = HTTPServer(("127.0.0.1", 8080), RequestHandler)
    print("HTTP Server started on http://127.0.0.1:8080")
    http_server.serve_forever()

if __name__ == "__main__":
    try:
        from jnius import autoclass
        PythonJavaClass = autoclass('org.renpy.android.PythonActivity')
        print("Running on Android")
    except:
        print("Running on Desktop")
    
    threading.Thread(target=start_server, daemon=True).start()
    
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        if http_server:
            http_server.shutdown()
