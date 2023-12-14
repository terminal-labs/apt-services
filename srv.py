import os
import sys
import uuid
import hashlib
import socket
import socketserver
from pathlib import Path
from shutil import copyfile
from shutil import move
from shutil import rmtree

convention = {
    "get": "GET ",
    "httpversion": "HTTP/",
    "host": "Host: ",
    "useragent": "User-Agent: ",
}
rdict = {
    "get": False,
    "httpversion": False,
    "host": False,
    "useragent": False,
    "name": False,
    "raw": False,
}

def dir_exists(path):
    return os.path.isdir(path)

def dir_create(path):
    if not os.path.exists(path):
        os.makedirs(path)

def dir_delete(path):
    try:
        rmtree(path)
    except FileNotFoundError:
        pass

def dir_listfiles(path):
    list_of_files = [f for f in os.listdir(path) if os.path.isfile("data/" + f)]
    return list_of_files

def dir_listdirs(path):
    list_of_dirs = [d for d in os.listdir(path) if os.path.isdir("data/" + d)]
    return list_of_dirs
 
def file_delete(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass

def file_copy(src, dst):
    copyfile(src, dst)

def file_rename(src, dst):
    os.rename(src, dst)

def file_move(src, dst):
    move(src, dst)

def file_sha256sum(filename):
    with open(filename, 'rb', buffering=0) as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def to_byte(data):
    return bytes(data.encode('utf-8'))

def to_str(data):
    return str(data.decode('utf-8'))

def get_user_home():
    return str(Path.home())

def download_to_buffer(rdict):
    request = rdict["raw"] 
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("archive.ubuntu.com", 80))
    s.send(request.encode())

    chunks = []
    with open("test.deb", 'wb') as file_to_write:
        while True:
            data = s.recv(1024)
            if not data:
                break
            file_to_write.write(data)
            chunks.append(data)
    print(chunks[0]) 

def prep_object_dir(rdict):
    s = rdict["get"]
    hash_object = hashlib.sha256(bytes(s.encode('utf-8')))
    hex_dig = hash_object.hexdigest()
    dir_create("data/" + str(hex_dig))
    import configparser

    config = configparser.ConfigParser()
    config['DEFAULT']['source'] = rdict["get"]
    config['DEFAULT']['hash'] = 'test'
    config['DEFAULT']['size'] = 'test'
    config['DEFAULT']['name'] = rdict["get"].split('/')[-1]
    with open("data/" + str(hex_dig) + '/FILE.INI', 'w') as configfile:
        config.write(configfile)
    print(dir_listdirs("data"))
    print(dir_listfiles("data"))

def request_serialise(r):
    def request_dict_verify(rdict):
        return rdict

    def request_pattern(line, search):
        line = line.strip()
        if search == "get":
            if line.startswith(convention["get"]):
                if " " in line:
                    return line[len(convention["get"]):].split(" ")[0]
                else:
                    return line[len(convention["get"]):]
        if search == "httpversion":
            if line.startswith(convention["get"]):
                if " " in line:
                    substr = line[len(convention["httpversion"]):].split(" ")[1]
                    if substr.startswith(convention["httpversion"]):
                        return substr
        if search == "name":
            if line.startswith(convention["get"]):
                if " " in line:
                    substr = line[len(convention["get"]):].split(" ")[0]
                    return substr.split('/')[-1]
        if search == "host":
            if line.startswith(convention["host"]):
                return line[len(convention["host"]):]
        if search == "useragent":
            if line.startswith(convention["useragent"]):
                return line[len(convention["useragent"]):]
    
    global rdict
    r = to_str(r)
    rdict_local = dict(rdict)
    rdict_local["raw"] = str(r)
    lines = r.split('\n')
    for line in lines:
        if line.startswith(convention["get"]):
            rdict_local["get"] = str(request_pattern(line, "get"))
            rdict_local["name"] = str(request_pattern(line, "name"))
            rdict_local["httpversion"] = str(request_pattern(line, "httpversion"))
        if line.startswith(convention["host"]):
            rdict_local["host"] = str(request_pattern(line, "host"))
        if line.startswith(convention["useragent"]):
            rdict_local["useragent"] = str(request_pattern(line, "useragent"))
    return rdict_local

def response_serialise(r):
    pass

class Handler_TCPServer(socketserver.BaseRequestHandler):
    def handle(self):
        self.data = self.request.recv(1024)
        rdict = request_serialise(self.data)
        print(rdict)
        prep_object_dir(rdict)
        self.request.sendall(b"HTTP/1.1 304 Not Modified\r\nDate: Wed, 13 Dec 2023 10:43:33 GMT\r\nServer: Debian Apt-Cacher NG/3.7.4\r\n\r\n")

def main():
    try:
        dir_create("data")
        HOST, PORT = "0.0.0.0", 2002
        socketserver.TCPServer.allow_reuse_address = True
        tcp_server = socketserver.ThreadingTCPServer((HOST, PORT), Handler_TCPServer)
        tcp_server.serve_forever()
    except KeyboardInterrupt:
        tcp_server.shutdown()
        tcp_server.server_close()
        sys.exit(0)

if __name__ == "__main__":
    main()
