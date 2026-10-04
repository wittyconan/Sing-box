#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import signal
import time
import stat
import subprocess
import urllib.request
import urllib.error
import http.server
import socketserver
import threading
import platform
from pathlib import Path

# 环境变量配置
PORT = int(os.environ.get('PORT', 3000))       # http服务端口
SUB_PATH = os.environ.get('SUB_PATH', 'sub')   # 订阅token
config = {
    'UUID': os.environ.get('UUID', 'dea9012d-edc7-4b79-b75f-e58db0d67782'),
    'NEZHA_SERVER': os.environ.get('NEZHA_SERVER', ''),
    'NEZHA_PORT': os.environ.get('NEZHA_PORT', ''),
    'NEZHA_KEY': os.environ.get('NEZHA_KEY', ''),
    'ARGO_DOMAIN': os.environ.get('ARGO_DOMAIN', 'net2.982694.xyz'),
    'ARGO_AUTH': os.environ.get('ARGO_AUTH', 'eyJhIjoiYzE1MjZjNzg5Mjc3N2QwMDQzMTNhYmIyODIyMTM2YTIiLCJ0IjoiMmQ2ZDQ0YTItNGUxNy00NTNmLTlkNDYtMjMwODc5MmE1Y2JkIiwicyI6Ik4ySmtZV05pWlRJdFlUUXhZeTAwTXpBNExUbGxNR1F0WTJOaFpHUTBOemxpTVRWbSJ9eyJhIjoiYzE1MjZjNzg5Mjc3N2QwMDQzMTNhYmIyODIyMTM2YTIiLCJ0IjoiMmQ2ZDQ0YTItNGUxNy00NTNmLTlkNDYtMjMwODc5MmE1Y2JkIiwicyI6Ik4ySmtZV05pWlRJdFlUUXhZeTAwTXpBNExUbGxNR1F0WTJOaFpHUTBOemxpTVRWbSJ9'),
    'ARGO_PORT': os.environ.get('ARGO_PORT', '8001'),
    'CFIP': os.environ.get('CFIP', 'saas.sin.fan'),
    'CFPORT': os.environ.get('CFPORT', '443'),
    'NAME': os.environ.get('NAME', ''),
    'S5_PORT': os.environ.get('S5_PORT', '12345'),
    'HY2_PORT': os.environ.get('HY2_PORT', '13589'),
    'TUIC_PORT': os.environ.get('TUIC_PORT', '16985'),
    'ANYTLS_PORT': os.environ.get('ANYTLS_PORT', '22658'),
    'REALITY_PORT': os.environ.get('REALITY_PORT', '26778'),
    'ANYREALITY_PORT': os.environ.get('ANYREALITY_PORT', '60024'),
    'CHAT_ID': os.environ.get('CHAT_ID', ''),
    'BOT_TOKEN': os.environ.get('BOT_TOKEN', ''),
    'UPLOAD_URL': os.environ.get('UPLOAD_URL', ''),
    'FILE_PATH': os.environ.get('FILE_PATH', '.cache'),
    'DISABLE_ARGO': os.environ.get('DISABLE_ARGO', 'false'),
    'SHOW_LOG': os.environ.get('SHOW_LOG', 'true'),
}

def inject_curl_wget_shims():
    """在无 root 容器中注入 curl/wget 垫片，兼容协议补全与纯文本查询"""
    bin_dir = os.path.join(os.getcwd(), '.bin')
    os.makedirs(bin_dir, exist_ok=True)

    shim_content = f'''#!{sys.executable}
import sys
import urllib.request

args = sys.argv[1:]
url = None
out_file = None

i = 0
while i < len(args):
    arg = args[i]
    if arg in ('-o', '-O'):
        if i + 1 < len(args):
            out_file = args[i + 1]
            i += 1
    elif arg.startswith('-o'):
        out_file = arg[2:]
    elif arg.startswith('-O'):
        out_file = arg[2:]
    elif not arg.startswith('-'):
        url = arg
    i += 1

if not url:
    sys.exit(0)

# 补全缺失的 http:// 前缀（解决 unknown url type: 'ipv4.ip.sb'）
if not url.startswith('http://') and not url.startswith('https://'):
    url = 'http://' + url

try:
    req = urllib.request.Request(
        url, 
        headers={{"User-Agent": "curl/7.88.1"}}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read()
        if out_file:
            with open(out_file, 'wb') as f:
                f.write(content)
        else:
            # 没有 -o/-O 参数时（如查 IP），直接打印到标准输出
            sys.stdout.buffer.write(content)
            sys.stdout.flush()
except Exception as e:
    sys.exit(1)
'''

    for cmd in ['curl', 'wget']:
        target_path = os.path.join(bin_dir, cmd)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(shim_content)
        current_permissions = os.stat(target_path).st_mode
        os.chmod(target_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    os.environ['PATH'] = f"{bin_dir}:{os.environ.get('PATH', '')}"

def sleep(ms):
    time.sleep(ms / 1000)

def get_architecture():
    """获取系统架构"""
    arch = platform.machine().lower()
    system = platform.system().lower()
    
    if system in ['linux', 'darwin']:
        if arch in ['x86_64', 'amd64']:
            return 'amd64'
        elif arch in ['aarch64', 'arm64']:
            return 'arm64'
    
    raise Exception(f"Unsupported architecture: {system} {arch}")

def download_file(url, dest_path):
    opener = urllib.request.build_opener()
    opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'),
        ('Accept', '*/*'),
        ('Connection', 'keep-alive')
    ]
    
    urllib.request.install_opener(opener)
    
    try:
        urllib.request.urlretrieve(url, dest_path)
    except urllib.error.HTTPError as e:
        if os.path.exists(dest_path):
            os.unlink(dest_path)
        raise Exception(f"Download failed (HTTP {e.code}): {e.reason}")
    except urllib.error.URLError as e:
        if os.path.exists(dest_path):
            os.unlink(dest_path)
        raise Exception(f"Download failed (URL error): {str(e)}")
    except Exception as e:
        if os.path.exists(dest_path):
            os.unlink(dest_path)
        raise Exception(f"Download failed: {str(e)}")

def set_executable(file_path):
    """设置文件可执行权限"""
    try:
        current_permissions = os.stat(file_path).st_mode
        os.chmod(file_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception as e:
        raise Exception(f"Failed to set executable permission: {str(e)}")

def delete_file(file_path):
    """删除文件"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(f"Failed to delete file {file_path}: {str(e)}")

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """自定义HTTP请求处理器"""
    
    def do_GET(self):
        if self.path == '/':
            self.handle_root()
        elif self.path == f'/{SUB_PATH}':
            self.handle_sub()
        elif self.path == '/ps':
            self.handle_ps()
        else:
            self.send_error(404, '404 Not Found')
    
    def handle_root(self):
        try:
            html_path = os.path.join(os.path.dirname(__file__), 'index.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(data.encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(f"Hello world!<br><br>You can access /{SUB_PATH} to get your nodes!".encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))
    
    def handle_sub(self):
        sub_file_path = os.path.join(config['FILE_PATH'], 'sub.txt')
        try:
            if os.path.exists(sub_file_path):
                with open(sub_file_path, 'r', encoding='utf-8') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(data.encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(f"Sub file not ready yet. Please wait...".encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))
    
    def handle_ps(self):
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, check=True)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(result.stdout.encode('utf-8'))
        except subprocess.CalledProcessError as e:
            self.send_error(500, f'Error executing ps command: {str(e)}')
    
    def log_message(self, format, *args):
        pass

def start_http_server():
    """启动HTTP服务器"""
    handler = CustomHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('0.0.0.0', PORT), handler)
    
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return httpd

def cleanup(binary_path):
    delete_file(binary_path)

def main():
    binary_path = None
    httpd = None
    process = None
    
    try:
        # 1. 注入 curl 和 wget 虚拟执行环境
        inject_curl_wget_shims()

        # 2. 启动 HTTP 订阅/保活服务器
        httpd = start_http_server()
        print('✅  App is running')
        print(f'🌐  HTTP server is running on {PORT}')
        
        # 3. 匹配架构并下载主程序
        arch = get_architecture()
        download_url = 'https://amd64.eooce.com/sbsh' if arch == 'amd64' else 'https://arm64.eooce.com/sbsh'
        binary_path = os.path.join(os.getcwd(), 'sbsh')
        
        print(f"[*] Downloading core binary for {arch}...")
        download_file(download_url, binary_path)
        if not os.path.exists(binary_path):
            raise Exception('Download failed, binary does not exist')
        
        set_executable(binary_path)
        
        # 4. 注入环境变量并执行主程序
        env = os.environ.copy()
        env.update({k: str(v) for k, v in config.items()})
        
        process = subprocess.Popen(
            [binary_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # 实时输出主程序产生的节点日志
        def log_output():
            for line in process.stdout:
                print(line, end='', flush=True)
        
        log_thread = threading.Thread(target=log_output)
        log_thread.daemon = True
        log_thread.start()
        
        # 保持运行
        while True:
            if process.poll() is not None:
                print(f"\n[!] Process terminated with exit code {process.returncode}")
                break
            time.sleep(1)
            
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        sys.exit(1)
    finally:
        if binary_path:
            cleanup(binary_path)
        if process and process.poll() is None:
            process.terminate()
        if httpd:
            httpd.shutdown()

def signal_handler(signum, frame):
    print("\nReceived signal to terminate")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
