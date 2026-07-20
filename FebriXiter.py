import webbrowser
import requests
import time
from datetime import datetime

# ================== KONFIGURASI ==================
WEBHOOK_URL = "https://discordapp.com/api/webhooks/1527730506374840542/8g6Yl0xV3vPF9xhRiI7wJraty3rNXlJZHE4dfz05oyRxUqv--JvIX-pkWOqvvQ-zMgwv"
WEBSITE_URL = "https://roast-grievance-cymbal.ngrok-free.dev"  # ✅ Hanya link ngrok saja
# =================================================

def send_to_discord() -> bool:
    current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    payload = {
        "content": "",
        "embeds": [
            {
                "title": "🔴 PANEL REMOT BY FEBRIXITERS",
                "description": f"📌 **ACCESS LINK**\n[Klik di sini untuk mengakses]({WEBSITE_URL})",
                "color": 16711680,
                "footer": {
                    "text": f"🕐 {current_time} WIB"
                }
            }
        ]
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal mengirim notifikasi: {e}")
        return False

def main() -> None:
    print("🚀 Menjalankan panel remote...")
    
    success = send_to_discord()
    
    if success:
        print("✅ Notifikasi berhasil dikirim ke Discord")
    else:
        print("⚠️ Gagal mengirim notifikasi, melanjutkan ke website...")
    
    try:
        print(f"🌐 Membuka website: {WEBSITE_URL}")
        webbrowser.open(WEBSITE_URL)
        time.sleep(1)
        print("✅ Website berhasil dibuka")
    except Exception as e:
        print(f"❌ Gagal membuka website: {e}")
    
    print("✨ Selesai!")

if __name__ == "__main__":
    main()