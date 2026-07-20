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

# ================== HIDE CONSOLE (WINDOWS) - DIKOMENTAR DULU BIAR KELIHATAN ERROR ==================
# if sys.platform == "win32":
#     try:
#         ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
#     except:
#         pass

# ================== KONFIGURASI ==================
APP_PORT = 4070
WEBHOOK_URL = "https://discordapp.com/api/webhooks/1527739484899119184/WxLSPY3SSGJ-iWDK_clHdWmyuU3CJHsKkUa4JCBIygQZAp3p9eijRI63IHE6YMJcI7_U"
NGROK_URL_FILE = "ngrok_url.txt"
NGROK_URL = None

# ================== FUNGSI NGROK YANG SUDAH DIPERBAIKI ==================
def get_ngrok_url():
    """Ambil URL ngrok dari API lokal"""
    try:
        response = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=5)
        if response.status_code == 200:
            data = response.json()
            for tunnel in data.get('tunnels', []):
                if tunnel.get('proto') == 'https':
                    url = tunnel.get('public_url')
                    if url:
                        return url
    except Exception as e:
        pass
    return None

def start_ngrok():
    """Jalankan ngrok otomatis - VERSI PALING STABIL"""
    global NGROK_URL
    
    try:
        # Cari ngrok.exe di berbagai lokasi
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
        
        # Cek di PATH environment
        if not ngrok_path:
            import shutil
            ngrok_path = shutil.which("ngrok")
        
        if not ngrok_path:
            print("❌ ngrok.exe tidak ditemukan!")
            print("📥 Download dari: https://ngrok.com/download")
            print("📁 Taruh file ngrok.exe di folder yang sama dengan app.py")
            return False
        
        print(f"✅ Ngrok ditemukan di: {ngrok_path}")
        
        # Set auth token
        print("🔑 Setting auth token...")
        try:
            subprocess.run(
                [ngrok_path, "config", "add-authtoken", "3GVSx6Oux7XIJxl0avTBSOtgj6Q_7wxpPx2Hb8ktuZ4nPVmk5"],
                capture_output=True,
                text=True,
                timeout=10
            )
            print("✅ Auth token berhasil di set")
        except Exception as e:
            print(f"⚠️ Gagal set token: {e}")
        
        # Cek apakah ngrok sudah berjalan
        print("🔍 Mengecek ngrok yang sudah berjalan...")
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
                            print(f"✅ Ngrok sudah berjalan! URL: {url}")
                            return True
        except:
            print("ℹ️ Ngrok belum berjalan, akan di-start...")
        
        # Jalankan ngrok di background
        print("🚀 Menjalankan ngrok...")
        subprocess.Popen(
            [ngrok_path, "http", str(APP_PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        
        # Tunggu ngrok siap (lebih lama)
        print("⏳ Menunggu ngrok siap...")
        for i in range(15):
            time.sleep(1)
            url = get_ngrok_url()
            if url:
                NGROK_URL = url
                with open(NGROK_URL_FILE, 'w') as f:
                    f.write(url)
                print(f"✅ Ngrok URL: {url}")
                return True
            if i % 3 == 0:
                print(f"   ⏳ Masih menunggu... ({i+1}/15)")
        
        print("❌ Gagal mendapatkan URL ngrok")
        print("💡 Solusi: Jalankan manual di CMD: ngrok http " + str(APP_PORT))
        return False
        
    except Exception as e:
        print(f"❌ Error start ngrok: {e}")
        return False

# ================== FUNGSI NOTIFIKASI ==================
def get_all_ips():
    """Dapatkan semua IP address lokal"""
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
    """Kirim notifikasi ke Discord"""
    global NGROK_URL
    
    # Ambil URL ngrok
    try:
        url = get_ngrok_url()
        if url:
            NGROK_URL = url
            with open(NGROK_URL_FILE, 'w') as f:
                f.write(url)
            print(f"✅ URL ngrok terupdate: {url}")
    except:
        pass
    
    try:
        hostname = socket.gethostname()
        ips = get_all_ips()
        current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        links = []
        if NGROK_URL:
            links.append(f"🌍 **PUBLIK (HP):** {NGROK_URL}/dashboard")
        
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
                {"name": "📱 Cara Akses", "value": "Klik link di atas dari HP", "inline": False}
            ],
            "footer": {"text": "FebriXiters Panel - Siap diakses dari mana saja"}
        }
        
        payload = {"content": "🔔 **PANEL TERSEDIA UNTUK DIAKSES!**", "embeds": [embed]}
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Notifikasi terkirim ke Discord!")
        else:
            print(f"⚠️ Discord response: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Gagal kirim notifikasi: {e}")

# ================== FLASK APP ==================
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'axc_corp_secure_key_2024'

@app.after_request
def add_ngrok_headers(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

messages = []
addresses = []
drag_addresses = []
user = {}
is32bit = True
isChangedDirectory = False
version = "1.0"
clear_triggered = False
notified_ips = set()
auto_clean_active = False
auto_clean_thread = None

# ================== KEYAUTH ==================
def getchecksum():
    import hashlib
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
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def inject_dll(pid, dll_path):
    """Inject DLL ke process"""
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        PROCESS_ALL_ACCESS = 0x1F0FFF
        h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not h_process:
            return False
        
        dll_path_bytes = dll_path.encode('utf-8')
        dll_len = len(dll_path_bytes) + 1
        allocated_mem = kernel32.VirtualAllocEx(
            h_process, None, dll_len, 0x1000, 0x40
        )
        if not allocated_mem:
            kernel32.CloseHandle(h_process)
            return False
        
        written = ctypes.c_size_t(0)
        if not kernel32.WriteProcessMemory(
            h_process, allocated_mem, dll_path_bytes, dll_len, ctypes.byref(written)
        ):
            kernel32.VirtualFreeEx(h_process, allocated_mem, 0, 0x8000)
            kernel32.CloseHandle(h_process)
            return False
        
        kernel32_handle = kernel32.GetModuleHandleW("kernel32.dll")
        loadlib_addr = kernel32.GetProcAddress(kernel32_handle, b"LoadLibraryA")
        if not loadlib_addr:
            kernel32.VirtualFreeEx(h_process, allocated_mem, 0, 0x8000)
            kernel32.CloseHandle(h_process)
            return False
        
        h_thread = kernel32.CreateRemoteThread(
            h_process, None, 0, loadlib_addr, allocated_mem, 0, None
        )
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
@app.before_request
def notify_on_access():
    # 🔴 NOTIFIKASI IP DIMATIKAN - LANGSUNG RETURN
    return
    # if request.path.startswith('/static/') or request.path.startswith('/favicon.ico'):
    #     return
    # if request.path in ['/auth', '/auth-check', '/logout', '/reset-notifications', '/clear-and-exit']:
    #     return
    # ip = request.remote_addr
    # if ip in notified_ips:
    #     return
    # notified_ips.add(ip)
    # threading.Thread(target=send_discord_ip_notification, args=(ip,)).start()

# 🔴 FUNGSI INI DIKOMENTARI (TIDAK DIPAKAI)
# def send_discord_ip_notification(ip_address="Unknown"):
#     try:
#         current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
#         url_to_send = NGROK_URL if NGROK_URL else f"http://127.0.0.1:{APP_PORT}"
#         payload = {
#             "content": "",
#             "embeds": [{
#                 "title": "🔴 PANEL REMOT BY FEBRIXITERS",
#                 "description": f"📌 **ACCESS LINK**\n[Klik di sini untuk mengakses]({url_to_send}/dashboard)",
#                 "color": 16711680,
#                 "fields": [
#                     {"name": "🌐 IP Address", "value": ip_address, "inline": True},
#                     {"name": "🕐 Waktu", "value": f"{current_time} WIB", "inline": True}
#                 ],
#                 "footer": {"text": "FebriXiters Panel - Auto Notify"}
#             }]
#         }
#         requests.post(WEBHOOK_URL, json=payload, timeout=5)
#     except:
#         pass

@app.route('/reset-notifications', methods=['POST'])
def reset_notifications():
    global notified_ips
    notified_ips.clear()
    return jsonify(status=200, message="Notifikasi reset")

@app.route('/clear-and-exit', methods=['POST'])
def clear_and_exit():
    global clear_triggered
    try:
        success = clear_all_traces()
        try:
            keyauthapp.logout()
        except:
            pass
        session.clear()
        global messages
        messages = []
        clear_triggered = True
        return jsonify(status=200, message="All traces cleared, logged out, and exited")
    except Exception as e:
        return jsonify(status=500, message=str(e))

def clear_all_traces():
    try:
        log_patterns = ['*.log', '*.logs', '*.tmp', '*.temp', '*.cache', '*.session']
        for pattern in log_patterns:
            for file in glob.glob(pattern):
                try:
                    os.remove(file)
                except:
                    pass
        return True
    except:
        return False

@app.get('/')
def homePage():
    if keyauthapp and keyauthapp.user_data.username:
        return redirect('/dashboard')
    return render_template('Homepage.html')

@app.get('/dashboard')
def dashboard():
    global user
    if keyauthapp and keyauthapp.user_data.username:
        if not user:
            user['username'] = keyauthapp.user_data.username
            user['hwid'] = keyauthapp.user_data.hwid
            user['ip'] = keyauthapp.user_data.ip
            if keyauthapp.user_data.expires:
                dt_object = datetime.datetime.fromtimestamp(int(keyauthapp.user_data.expires))
                user['expiry'] = dt_object.strftime('%Y-%m-%d %H:%M:%S')
        return render_template('Dashboard.html', user=user, version=keyauthapp.version)
    return redirect('/')

@app.get('/settings')
def settings():
    if keyauthapp and keyauthapp.user_data.username:
        return render_template('Settings.html')
    return redirect('/')

@app.post('/auth')
def auth():
    if request.method == "POST":
        data = request.get_json()
        try:
            reply = keyauthapp.login(user=data['username'], password=data['password'])
            if reply:
                user['username'] = keyauthapp.user_data.username
                user['hwid'] = keyauthapp.user_data.hwid
                user['ip'] = keyauthapp.user_data.ip
                dt_object = datetime.datetime.fromtimestamp(int(keyauthapp.user_data.expires))
                user['expiry'] = dt_object.strftime('%Y-%m-%d %H:%M:%S')
                now = datetime.datetime.now()
                messages.append(now.strftime("%H:%M:%S") + f" Logged in as {keyauthapp.user_data.username}")
                return jsonify(status=200, message="logged in")
            else:
                return jsonify(status=301, message="Credentials Mismatch")
        except:
            return jsonify(status=301, message="Credentials Mismatch")

@app.post('/auth-check')
def authCheck():
    if not user:
        return jsonify(status=302)
    return jsonify(status=200)

@app.get('/logout')
def logout():
    try:
        reply = keyauthapp.logout()
        return jsonify(status=200 if reply else 303)
    except:
        return jsonify(status=303)

@app.post('/logs')
def logs():
    global messages
    return jsonify(status=200, message=messages[::-1])

@app.post('/user-info')
def userInfo():
    try:
        onlineUsers = keyauthapp.fetchOnline()
        OU = ''
        if onlineUsers:
            OU = ' '.join([u["credential"] for u in onlineUsers])
        else:
            OU = "No online users"
        return jsonify(
            status=200,
            username=user.get('username', 'N/A'),
            ipAddress=user.get('ip', 'N/A'),
            hwid=user.get('hwid', 'N/A'),
            expiry=user.get('expiry', 'N/A'),
            onlineUsers=OU
        )
    except:
        return jsonify(
            status=200,
            username=user.get('username', 'N/A'),
            ipAddress=user.get('ip', 'N/A'),
            hwid=user.get('hwid', 'N/A'),
            expiry=user.get('expiry', 'N/A'),
            onlineUsers="No online users"
        )

# ================== ROUTES GAME ==================
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
    global addresses
    try:
        addresses = Memory.aimbot_load()
        if addresses:
            messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimbot Load Done")
            return jsonify(status=200)
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimbot Load Error")
        return jsonify(status=304)
    except:
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimbot Load Error")
        return jsonify(status=304)

@app.post('/aimbot-on')
def aimbotOn():
    global addresses
    try:
        Memory.aimbot_on(addresses)
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimbot On Done")
        return jsonify(status=200)
    except:
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimbot On Failed")
        return jsonify(status=304)

@app.post('/aimbot-off')
def aimbotOff():
    global addresses
    try:
        Memory.aimbot_off(addresses)
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimbot Off Done")
        return jsonify(status=200)
    except:
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimbot Off Failed")
        return jsonify(status=304)

@app.post('/aimdrag-load')
def aimDragLoad():
    global drag_addresses
    try:
        drag_addresses = Memory.drag_load()
        if drag_addresses:
            messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimdrag Load Done")
            return jsonify(status=200)
        return jsonify(status=304)
    except:
        return jsonify(status=304)

@app.post('/aimdrag-on')
def aimDragOn():
    global drag_addresses
    try:
        Memory.aimdrag_on(drag_addresses)
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimdrag On Done")
        return jsonify(status=200)
    except:
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimdrag On Failed")
        return jsonify(status=304)

@app.post('/aimdrag-off')
def aimDragOff():
    global drag_addresses
    try:
        Memory.aimdrag_off(drag_addresses)
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ✅ Aimdrag Off Done")
        return jsonify(status=200)
    except:
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ❌ Aimdrag Off Failed")
        return jsonify(status=304)

@app.post('/update-bit32')
def bit32():
    global is32bit
    is32bit = True
    messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " 32 bit FreeFire Selected")
    return jsonify(status=200)

@app.post('/update-bit64')
def bit64():
    global is32bit
    is32bit = False
    messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " 64 bit FreeFire Selected")
    return jsonify(status=200)

# ================== FUNGSI CLEAN (DIPISAHKAN DARI ROUTE) ==================
def perform_basic_clean():
    """Fungsi internal untuk Basic Clean"""
    cleaned = 0
    
    # 1. Bersihkan file temporary
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
    
    # 2. Bersihkan file log di direktori saat ini
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
    """Fungsi internal untuk Deep Clean"""
    cleaned = 0
    
    # 1. Bersihkan temporary files
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
    
    # 2. Bersihkan prefetch
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
    
    # 3. Bersihkan recycle bin
    try:
        ctypes.windll.shell32.SHEmptyRecycleBinW(0, None, 0x00000001)
        cleaned += 1
    except:
        pass
    
    # 4. Bersihkan file temporary Windows
    try:
        subprocess.run(['cleanmgr', '/sagerun:1'], capture_output=True, timeout=30)
        cleaned += 1
    except:
        pass
    
    # 5. Bersihkan log aplikasi
    log_patterns = ['*.log', '*.logs', '*.tmp', '*.temp', '*.cache', '*.session', '*.pyc']
    for pattern in log_patterns:
        for file in glob.glob(pattern):
            try:
                os.remove(file)
                cleaned += 1
            except:
                pass
    
    # 6. Bersihkan cache browser
    browser_cache_dirs = [
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache')
    ]
    
    for cache_dir in browser_cache_dirs:
        if os.path.exists(cache_dir):
            for root, dirs, files in os.walk(cache_dir):
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                        cleaned += 1
                    except:
                        pass
    
    return cleaned

# ================== ROUTES SPECIAL FEATURES ==================
@app.post('/auto-start')
def auto_start():
    """Auto Start After Restart - Menjalankan ulang panel secara otomatis"""
    try:
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " 🔄 Auto Start Initiated - Restarting panel...")
        
        # Simpan flag untuk auto restart
        with open('auto_restart.flag', 'w') as f:
            f.write('1')
        
        # Fungsi untuk restart
        def restart_panel():
            time.sleep(1)
            python = sys.executable
            os.execl(python, python, *sys.argv)
        
        # Jalankan di thread terpisah
        restart_thread = threading.Thread(target=restart_panel, daemon=True)
        restart_thread.start()
        
        return jsonify(status=200, message="Panel restarting...")
    except Exception as e:
        return jsonify(status=500, message=str(e))

@app.post('/basic-clean')
def basic_clean():
    """Basic Clean - Membersihkan file-file sementara"""
    try:
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " 🧹 Basic Clean Started...")
        cleaned = perform_basic_clean()
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + f" ✅ Basic Clean Done - {cleaned} files cleaned")
        return jsonify(status=200, message=f"Basic clean completed - {cleaned} files cleaned")
    except Exception as e:
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + f" ❌ Basic Clean Failed: {str(e)}")
        return jsonify(status=500, message=str(e))

@app.post('/deep-clean')
def deep_clean():
    """Deep Clean - Membersihkan semua jejak secara mendalam"""
    try:
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " 🔥 Deep Clean Started...")
        cleaned = perform_deep_clean()
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + f" ✅ Deep Clean Done - {cleaned} files cleaned")
        return jsonify(status=200, message=f"Deep clean completed - {cleaned} files cleaned")
    except Exception as e:
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + f" ❌ Deep Clean Failed: {str(e)}")
        return jsonify(status=500, message=str(e))

@app.post('/auto-deep-clean')
def auto_deep_clean():
    """Auto Deep Clean - Membersihkan secara otomatis dengan interval"""
    global auto_clean_active, auto_clean_thread
    
    try:
        if auto_clean_active:
            return jsonify(status=200, message="Auto Deep Clean already active")
        
        auto_clean_active = True
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " 🤖 Auto Deep Clean Activated - Cleaning every 30 minutes")
        
        def run_auto_clean():
            global auto_clean_active
            # Gunakan app.app_context() untuk akses ke Flask context
            with app.app_context():
                while auto_clean_active:
                    try:
                        # Lakukan deep clean
                        cleaned = perform_deep_clean()
                        current_time = datetime.datetime.now().strftime("%H:%M:%S")
                        messages.append(f"{current_time} 🔄 Auto Deep Clean Executed - {cleaned} files cleaned")
                    except Exception as e:
                        current_time = datetime.datetime.now().strftime("%H:%M:%S")
                        messages.append(f"{current_time} ❌ Auto Deep Clean Error: {str(e)}")
                    
                    # Tunggu 30 menit
                    for _ in range(1800):  # 30 menit = 1800 detik
                        if not auto_clean_active:
                            break
                        time.sleep(1)
        
        # Jalankan di thread terpisah
        auto_clean_thread = threading.Thread(target=run_auto_clean, daemon=True)
        auto_clean_thread.start()
        
        return jsonify(status=200, message="Auto Deep Clean activated - cleaning every 30 minutes")
    except Exception as e:
        return jsonify(status=500, message=str(e))

@app.post('/stop-auto-clean')
def stop_auto_clean():
    """Stop Auto Deep Clean"""
    global auto_clean_active
    try:
        auto_clean_active = False
        messages.append(datetime.datetime.now().strftime("%H:%M:%S") + " ⏹ Auto Deep Clean Stopped")
        return jsonify(status=200, message="Auto Deep Clean stopped")
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
    """Jalankan Flask server"""
    def send_start_notif():
        time.sleep(5)  # Tunggu lebih lama biar ngrok siap
        send_server_start_notification()
    
    threading.Thread(target=send_start_notif, daemon=True).start()
    
    print("\n" + "="*60)
    print("🚀 SERVER FEBRIXITERS PANEL")
    print("="*60)
    print(f"📍 URL LOKAL: http://127.0.0.1:{APP_PORT}/dashboard")
    
    ip_list = get_all_ips()
    for ip in ip_list:
        if ip != '127.0.0.1':
            print(f"📍 URL LAN: http://{ip}:{APP_PORT}/dashboard")
    
    if NGROK_URL:
        print(f"🌍 URL PUBLIK: {NGROK_URL}/dashboard")
        print("📱 BUKA DARI HP: " + NGROK_URL + "/dashboard")
    
    print("="*60)
    print("")
    
    app.run(debug=False, host='0.0.0.0', port=APP_PORT, threaded=True, use_reloader=False)

# ================== MAIN ==================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔥 FEBRIXITERS PANEL STARTING...")
    print("="*60)
    
    # START NGROK OTOMATIS
    print("\n🔄 Menjalankan Ngrok...")
    ngrok_started = start_ngrok()
    
    if ngrok_started and NGROK_URL:
        print(f"\n✅ NGROK BERHASIL!")
        print(f"🌍 URL PUBLIK: {NGROK_URL}/dashboard")
        print("📱 BUKA DARI HP: " + NGROK_URL + "/dashboard")
    else:
        print("\n⚠️ Ngrok gagal, panel hanya bisa diakses secara lokal")
        print("💡 Solusi: Jalankan 'ngrok http 4070' di CMD terpisah")
    
    # Jalankan semua thread
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