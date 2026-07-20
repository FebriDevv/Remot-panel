import os
import sys
import ctypes
import datetime
import threading
import time
import subprocess
import pymem
from flask import Flask, jsonify, redirect, render_template, request, session, current_app
from keyauth import api
import Memory
import utils
import shutil
import tempfile
import winreg
import requests
import glob
import socket
import json
import hashlib
import secrets

# ================== HIDE CONSOLE ==================
if sys.platform == "win32":
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

# ================== KONFIGURASI ==================
APP_PORT = int(os.environ.get('PORT', 4070))
IS_RENDER = os.environ.get('RENDER') is not None
WEBHOOK_URL = "https://discordapp.com/api/webhooks/1527739484899119184/WxLSPY3SSGJ-iWDK_clHdWmyuU3CJHsKkUa4JCBIygQZAp3p9eijRI63IHE6YMJcI7_U"
NGROK_URL_FILE = "ngrok_url.txt"
NGROK_URL = None

# ================== DATA PER-USER (MULTI-USER SESSION) ==================
user_sessions = {}  # { username: { data } }

def get_user_session(username):
    if username not in user_sessions:
        user_sessions[username] = {
            'messages': [],
            'addresses': [],
            'drag_addresses': [],
            'is32bit': True,
            'isChangedDirectory': False,
            'clear_triggered': False,
            'notified_ips': set(),
            'auto_clean_active': False,
            'auto_clean_thread': None,
            'user_info': {},
            'logged_in_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    return user_sessions[username]

def get_current_user():
    return session.get('username')

# ================== FUNGSI NGROK ==================
def get_ngrok_url():
    try:
        response = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=5)
        if response.status_code == 200:
            data = response.json()
            for tunnel in data.get('tunnels', []):
                if tunnel.get('proto') == 'https':
                    url = tunnel.get('public_url')
                    if url:
                        return url
    except:
        pass
    return None

def start_ngrok():
    global NGROK_URL
    # Skip kalo di Render
    if IS_RENDER:
        return False
    try:
        ngrok_paths = [
            "ngrok.exe",
            os.path.join(os.path.dirname(sys.argv[0]), "ngrok.exe"),
            os.path.join(os.getcwd(), "ngrok.exe")
        ]
        ngrok_path = None
        for path in ngrok_paths:
            if os.path.exists(path):
                ngrok_path = path
                break
        if not ngrok_path:
            ngrok_path = shutil.which("ngrok")
        if not ngrok_path:
            print("❌ ngrok.exe tidak ditemukan!")
            return False
        print(f"✅ Ngrok ditemukan di: {ngrok_path}")
        try:
            subprocess.run(
                [ngrok_path, "config", "add-authtoken", "3GVSx6Oux7XIJxl0avTBSOtgj6Q_7wxpPx2Hb8ktuZ4nPVmk5"],
                capture_output=True,
                text=True,
                timeout=10
            )
        except:
            pass
        try:
            response = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=3)
            if response.status_code == 200:
                data = response.json()
                for tunnel in data.get('tunnels', []):
                    if tunnel.get('proto') == 'https':
                        url = tunnel.get('public_url')
                        if url:
                            NGROK_URL = url
                            with open(NGROK_URL_FILE, 'w') as f:
                                f.write(url)
                            return True
        except:
            pass
        subprocess.Popen(
            [ngrok_path, "http", str(APP_PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        for i in range(15):
            time.sleep(1)
            url = get_ngrok_url()
            if url:
                NGROK_URL = url
                with open(NGROK_URL_FILE, 'w') as f:
                    f.write(url)
                return True
        return False
    except:
        return False

# ================== FUNGSI NOTIFIKASI ==================
def get_all_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        host_ips = socket.gethostbyname_ex(hostname)
        for ip in host_ips[2]:
            if ip not in ips and ip != '127.0.0.1':
                ips.append(ip)
    except:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if ip not in ips and ip != '127.0.0.1':
            ips.append(ip)
        s.close()
    except:
        pass
    if not ips:
        ips.append('127.0.0.1')
    return ips

def send_server_start_notification():
    global NGROK_URL
    try:
        url = get_ngrok_url()
        if url:
            NGROK_URL = url
            with open(NGROK_URL_FILE, 'w') as f:
                f.write(url)
    except:
        pass
    try:
        hostname = socket.gethostname()
        ips = get_all_ips()
        current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        links = []
        if NGROK_URL:
            links.append(f"🌍 **PUBLIK:** {NGROK_URL}/dashboard")
        for ip in ips:
            if ip != '127.0.0.1':
                links.append(f"📱 **LAN:** http://{ip}:{APP_PORT}/dashboard")
        links.append(f"💻 **LOKAL:** http://127.0.0.1:{APP_PORT}/dashboard")
        embed = {
            "title": "🟢 PANEL FEBRIXITERS ONLINE!",
            "description": "\n".join(links),
            "color": 65280,
            "fields": [
                {"name": "🕐 Waktu", "value": current_time, "inline": True},
                {"name": "💻 Hostname", "value": hostname, "inline": True},
                {"name": "👥 Multi-User", "value": f"{len(user_sessions)} user sessions active", "inline": False}
            ],
            "footer": {"text": "FebriXiters Panel - Multi-User Mode"}
        }
        payload = {"content": "🔔 **PANEL TERSEDIA UNTUK DIAKSES!**", "embeds": [embed]}
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
    except:
        pass

# ================== FLASK APP ==================
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

@app.after_request
def add_ngrok_headers(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

# ================== KEYAUTH ==================
def getchecksum():
    md5_hash = hashlib.md5()
    try:
        with open(sys.argv[0], "rb") as file:
            md5_hash.update(file.read())
    except:
        pass
    return md5_hash.hexdigest()

keyauthapp = api(
    name="FebriXiters",
    ownerid="QwwNOHpTII",
    secret="ae2984201557730393accb19c9ebad16b9751d56bfb3e0752baa3f1428ddce38",
    version="1.0",
    hash_to_check=getchecksum()
)

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def inject_dll(pid, dll_path):
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        PROCESS_ALL_ACCESS = 0x1F0FFF
        h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not h_process:
            return False
        dll_path_bytes = dll_path.encode('utf-8')
        dll_len = len(dll_path_bytes) + 1
        allocated_mem = kernel32.VirtualAllocEx(h_process, None, dll_len, 0x1000, 0x40)
        if not allocated_mem:
            kernel32.CloseHandle(h_process)
            return False
        written = ctypes.c_size_t(0)
        if not kernel32.WriteProcessMemory(h_process, allocated_mem, dll_path_bytes, dll_len, ctypes.byref(written)):
            kernel32.VirtualFreeEx(h_process, allocated_mem, 0, 0x8000)
            kernel32.CloseHandle(h_process)
            return False
        kernel32_handle = kernel32.GetModuleHandleW("kernel32.dll")
        loadlib_addr = kernel32.GetProcAddress(kernel32_handle, b"LoadLibraryA")
        if not loadlib_addr:
            kernel32.VirtualFreeEx(h_process, allocated_mem, 0, 0x8000)
            kernel32.CloseHandle(h_process)
            return False
        h_thread = kernel32.CreateRemoteThread(h_process, None, 0, loadlib_addr, allocated_mem, 0, None)
        if not h_thread:
            kernel32.VirtualFreeEx(h_process, allocated_mem, 0, 0x8000)
            kernel32.CloseHandle(h_process)
            return False
        kernel32.WaitForSingleObject(h_thread, 0xFFFFFFFF)
        kernel32.CloseHandle(h_thread)
        kernel32.VirtualFreeEx(h_process, allocated_mem, 0, 0x8000)
        kernel32.CloseHandle(h_process)
        return True
    except:
        return False

inject = inject_dll

# ================== ROUTES ==================
@app.route('/')
def homePage():
    if get_current_user() and keyauthapp.user_data.username:
        return redirect('/dashboard')
    return render_template('Homepage.html')

@app.route('/dashboard')
def dashboard():
    username = get_current_user()
    if not username or not keyauthapp.user_data.username:
        return redirect('/')
    user = get_user_session(username)
    user_info = user.get('user_info', {})
    return render_template('Dashboard.html', user=user_info, version=keyauthapp.version, username=username)

@app.route('/settings')
def settings():
    if not get_current_user():
        return redirect('/')
    return render_template('Settings.html')

@app.post('/auth')
def auth():
    data = request.get_json()
    try:
        reply = keyauthapp.login(user=data['username'], password=data['password'])
        if reply:
            username = keyauthapp.user_data.username
            session['username'] = username
            user = get_user_session(username)
            user['user_info'] = {
                'username': username,
                'hwid': keyauthapp.user_data.hwid,
                'ip': keyauthapp.user_data.ip,
                'expiry': datetime.datetime.fromtimestamp(int(keyauthapp.user_data.expires)).strftime('%Y-%m-%d %H:%M:%S') if keyauthapp.user_data.expires else 'Lifetime'
            }
            now = datetime.datetime.now()
            user['messages'].append(now.strftime("%H:%M:%S") + f" ✅ Logged in as {username}")
            return jsonify(status=200, message="logged in")
        else:
            return jsonify(status=301, message="Credentials Mismatch")
    except:
        return jsonify(status=301, message="Credentials Mismatch")

@app.post('/auth-check')
def authCheck():
    username = get_current_user()
    if not username:
        return jsonify(status=302)
    return jsonify(status=200)

@app.get('/logout')
def logout():
    username = get_current_user()
    if username:
        try:
            keyauthapp.logout()
        except:
            pass
        session.pop('username', None)
    return jsonify(status=200)

@app.post('/logs')
def logs():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    return jsonify(status=200, message=user['messages'][::-1])

@app.post('/user-info')
def userInfo():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        onlineUsers = keyauthapp.fetchOnline()
        OU = ' '.join([u["credential"] for u in onlineUsers]) if onlineUsers else "No online users"
    except:
        OU = "No online users"
    user_info = user.get('user_info', {})
    return jsonify(
        status=200,
        username=user_info.get('username', 'N/A'),
        ipAddress=user_info.get('ip', 'N/A'),
        hwid=user_info.get('hwid', 'N/A'),
        expiry=user_info.get('expiry', 'N/A'),
        onlineUsers=OU,
        activeSessions=len(user_sessions)
    )

@app.route('/reset-notifications', methods=['POST'])
def reset_notifications():
    username = get_current_user()
    if username:
        user = get_user_session(username)
        user['notified_ips'].clear()
    return jsonify(status=200, message="Notifikasi reset")

@app.route('/clear-and-exit', methods=['POST'])
def clear_and_exit():
    username = get_current_user()
    if username:
        user = get_user_session(username)
        user['clear_triggered'] = True
        try:
            keyauthapp.logout()
        except:
            pass
        session.pop('username', None)
    return jsonify(status=200, message="Logged out and cleared")

# ================== ROUTES GAME (PER-USER) ==================
@app.post('/get-process')
def getProcess():
    try:
        status = Memory.get_process("HD-Player.exe")
        if not status:
            return jsonify(status=303)
        return jsonify(status=200, pid=status)
    except:
        return jsonify(status=303)

@app.post('/aimbot-load')
def aimbotLoad():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        addresses = Memory.aimbot_load()
        if addresses:
            user['addresses'] = addresses
            user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimbot Load Done")
            return jsonify(status=200)
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimbot Load Error")
        return jsonify(status=304)
    except:
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimbot Load Error")
        return jsonify(status=304)

@app.post('/aimbot-on')
def aimbotOn():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        Memory.aimbot_on(user['addresses'])
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimbot On Done")
        return jsonify(status=200)
    except:
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimbot On Failed")
        return jsonify(status=304)

@app.post('/aimbot-off')
def aimbotOff():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        Memory.aimbot_off(user['addresses'])
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimbot Off Done")
        return jsonify(status=200)
    except:
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimbot Off Failed")
        return jsonify(status=304)

@app.post('/aimdrag-load')
def aimDragLoad():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        drag_addresses = Memory.drag_load()
        if drag_addresses:
            user['drag_addresses'] = drag_addresses
            user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimdrag Load Done")
            return jsonify(status=200)
        return jsonify(status=304)
    except:
        return jsonify(status=304)

@app.post('/aimdrag-on')
def aimDragOn():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        Memory.aimdrag_on(user['drag_addresses'])
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimdrag On Done")
        return jsonify(status=200)
    except:
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimdrag On Failed")
        return jsonify(status=304)

@app.post('/aimdrag-off')
def aimDragOff():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        Memory.aimdrag_off(user['drag_addresses'])
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimdrag Off Done")
        return jsonify(status=200)
    except:
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimdrag Off Failed")
        return jsonify(status=304)

@app.post('/update-bit32')
def bit32():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    user['is32bit'] = True
    user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " 32 bit FreeFire Selected")
    return jsonify(status=200)

@app.post('/update-bit64')
def bit64():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    user['is32bit'] = False
    user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " 64 bit FreeFire Selected")
    return jsonify(status=200)

# ================== FUNGSI CLEAN ==================
def perform_basic_clean():
    cleaned = 0
    temp_dirs = [
        os.environ.get('TEMP', ''),
        os.environ.get('TMP', ''),
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp')
    ]
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            try:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        try:
                            os.remove(os.path.join(root, file))
                            cleaned += 1
                        except:
                            pass
            except:
                pass
    log_patterns = ['*.log', '*.logs', '*.tmp', '*.temp', '*.cache']
    for pattern in log_patterns:
        for file in glob.glob(pattern):
            try:
                os.remove(file)
                cleaned += 1
            except:
                pass
    return cleaned

def perform_deep_clean():
    cleaned = 0
    temp_dirs = [
        os.environ.get('TEMP', ''),
        os.environ.get('TMP', ''),
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp'),
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp', '*.tmp'),
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp', '*.log')
    ]
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            try:
                if '*' in temp_dir:
                    for file in glob.glob(temp_dir):
                        try:
                            os.remove(file)
                            cleaned += 1
                        except:
                            pass
                else:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            try:
                                os.remove(os.path.join(root, file))
                                cleaned += 1
                            except:
                                pass
            except:
                pass
    try:
        prefetch_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Prefetch')
        if os.path.exists(prefetch_dir):
            for file in glob.glob(os.path.join(prefetch_dir, '*.pf')):
                try:
                    os.remove(file)
                    cleaned += 1
                except:
                    pass
    except:
        pass
    try:
        ctypes.windll.shell32.SHEmptyRecycleBinW(0, None, 0x00000001)
        cleaned += 1
    except:
        pass
    try:
        subprocess.run(['cleanmgr', '/sagerun:1'], capture_output=True, timeout=30)
        cleaned += 1
    except:
        pass
    log_patterns = ['*.log', '*.logs', '*.tmp', '*.temp', '*.cache', '*.session', '*.pyc']
    for pattern in log_patterns:
        for file in glob.glob(pattern):
            try:
                os.remove(file)
                cleaned += 1
            except:
                pass
    return cleaned

# ================== ROUTES CLEAN (PER-USER) ==================
@app.post('/basic-clean')
def basic_clean():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " 🧹 Basic Clean Started...")
        cleaned = perform_basic_clean()
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + f" ✅ Basic Clean Done - {cleaned} files cleaned")
        return jsonify(status=200, message=f"Basic clean completed - {cleaned} files cleaned")
    except Exception as e:
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + f" ❌ Basic Clean Failed: {str(e)}")
        return jsonify(status=500, message=str(e))

@app.post('/deep-clean')
def deep_clean():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " 🔥 Deep Clean Started...")
        cleaned = perform_deep_clean()
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + f" ✅ Deep Clean Done - {cleaned} files cleaned")
        return jsonify(status=200, message=f"Deep clean completed - {cleaned} files cleaned")
    except Exception as e:
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + f" ❌ Deep Clean Failed: {str(e)}")
        return jsonify(status=500, message=str(e))

@app.post('/auto-deep-clean')
def auto_deep_clean():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        if user['auto_clean_active']:
            return jsonify(status=200, message="Auto Deep Clean already active")
        user['auto_clean_active'] = True
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " 🤖 Auto Deep Clean Activated - Cleaning every 30 minutes")
        def run_auto_clean():
            with app.app_context():
                while user['auto_clean_active']:
                    try:
                        cleaned = perform_deep_clean()
                        current_time = datetime.datetime.now().strftime("%H:%M:%S")
                        user['messages'].append(f"{current_time} 🔄 Auto Deep Clean Executed - {cleaned} files cleaned")
                    except Exception as e:
                        current_time = datetime.datetime.now().strftime("%H:%M:%S")
                        user['messages'].append(f"{current_time} ❌ Auto Deep Clean Error: {str(e)}")
                    for _ in range(1800):
                        if not user['auto_clean_active']:
                            break
                        time.sleep(1)
        user['auto_clean_thread'] = threading.Thread(target=run_auto_clean, daemon=True)
        user['auto_clean_thread'].start()
        return jsonify(status=200, message="Auto Deep Clean activated - cleaning every 30 minutes")
    except Exception as e:
        return jsonify(status=500, message=str(e))

@app.post('/stop-auto-clean')
def stop_auto_clean():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        user['auto_clean_active'] = False
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " ⏹ Auto Deep Clean Stopped")
        return jsonify(status=200, message="Auto Deep Clean stopped")
    except Exception as e:
        return jsonify(status=500, message=str(e))

@app.post('/auto-start')
def auto_start():
    username = get_current_user()
    if not username:
        return jsonify(status=401, message="Not logged in")
    user = get_user_session(username)
    try:
        user['messages'].append(datetime.datetime.now().strftime("%H:%M:%S") + " 🔄 Auto Start Initiated - Restarting panel...")
        with open('auto_restart.flag', 'w') as f:
            f.write('1')
        def restart_panel():
            time.sleep(1)
            python = sys.executable
            os.execl(python, python, *sys.argv)
        restart_thread = threading.Thread(target=restart_panel, daemon=True)
        restart_thread.start()
        return jsonify(status=200, message="Panel restarting...")
    except Exception as e:
        return jsonify(status=500, message=str(e))

# ================== THREAD FUNCTIONS ==================
isTaskClose = True
isProcessClose = True

def taskManager():
    global isTaskClose
    time.sleep(2)
    while True:
        try:
            if utils.check_process("Taskmgr.exe") and isTaskClose:
                try:
                    pm = pymem.Pymem("Taskmgr.exe")
                    inject(pm.process_id, get_resource_path("dlls/alpha.dll"))
                    isTaskClose = False
                except:
                    pass
            elif not utils.check_process("Taskmgr.exe") and not isTaskClose:
                isTaskClose = True
            time.sleep(0.25)
        except:
            time.sleep(0.25)

def processManager():
    global isProcessClose
    time.sleep(2)
    while True:
        try:
            if utils.check_process("ProcessHacker.exe") and isProcessClose:
                try:
                    pm2 = pymem.Pymem("ProcessHacker.exe")
                    inject(pm2.process_id, get_resource_path("dlls/alpha.dll"))
                    isProcessClose = False
                except:
                    pass
            elif not utils.check_process("ProcessHacker.exe") and not isProcessClose:
                isProcessClose = True
            time.sleep(0.25)
        except:
            time.sleep(0.25)

def run_flask():
    def send_start_notif():
        time.sleep(5)
        send_server_start_notification()
    threading.Thread(target=send_start_notif, daemon=True).start()
    print("\n" + "="*60)
    print("🚀 FEBRIXITERS PANEL - MULTI-USER MODE")
    print("="*60)
    print(f"📍 URL LOKAL: http://127.0.0.1:{APP_PORT}/dashboard")
    ip_list = get_all_ips()
    for ip in ip_list:
        if ip != '127.0.0.1':
            print(f"📍 URL LAN: http://{ip}:{APP_PORT}/dashboard")
    if NGROK_URL:
        print(f"🌍 URL PUBLIK: {NGROK_URL}/dashboard")
        print("📱 BUKA DARI HP: " + NGROK_URL + "/dashboard")
    if IS_RENDER:
        print(f"🌍 RENDER URL: https://{os.environ.get('RENDER_EXTERNAL_URL', 'unknown')}/dashboard")
    print(f"👥 Multi-User Mode: ACTIVE")
    print("="*60)
    app.run(debug=False, host='0.0.0.0', port=APP_PORT, threaded=True, use_reloader=False)

# ================== MAIN ==================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔥 FEBRIXITERS PANEL STARTING...")
    print("="*60)
    if IS_RENDER:
        print("\n✅ RENDER MODE DETECTED - Ngrok disabled")
    else:
        print("\n🔄 Menjalankan Ngrok...")
        ngrok_started = start_ngrok()
        if ngrok_started and NGROK_URL:
            print(f"\n✅ NGROK BERHASIL!")
            print(f"🌍 URL PUBLIK: {NGROK_URL}/dashboard")
        else:
            print("\n⚠️ Ngrok gagal, panel hanya bisa diakses secara lokal")
    flask_thread = threading.Thread(target=run_flask)
    task_thread = threading.Thread(target=taskManager)
    process_thread = threading.Thread(target=processManager)
    task_thread.daemon = True
    process_thread.daemon = True
    flask_thread.daemon = True
    task_thread.start()
    process_thread.start()
    flask_thread.start()
    try:
        flask_thread.join()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")