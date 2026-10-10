import paramiko
import socket
import threading
import sys

HOST = "0.0.0.0"
PORT = 2222
USERNAME = "root"
PASSWORD = "tEhQ8p93ceTynl8P"

class SSHServer(paramiko.ServerInterface):
    def check_auth_password(self, username, password):
        if username == USERNAME and password == PASSWORD:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

def handle_client(client):
    transport = paramiko.Transport(client)
    transport.add_server_key(paramiko.RSAKey.generate(2048))
    transport.start_server(server=SSHServer())

    chan = transport.accept(20)
    if chan is None:
        return

    chan.send("Connected.\r\n")
    chan.close()

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(10)
    print(f"Listening on {HOST}:{PORT}")

    while True:
        client, addr = sock.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()

if __name__ == "__main__":
    main()
