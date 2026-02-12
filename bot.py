import requests
from bs4 import BeautifulSoup
import json
import sys
import os  # <--- Library untuk mengambil kunci dari brankas
from datetime import datetime
import pytz

# ================= K O N F I G U R A S I =================
# KITA TIDAK LAGI MENULIS TOKEN DI SINI (BIAR AMAN)
# Token akan diambil otomatis dari GitHub Secrets
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

WATCHLIST = [
    "https://bibit.id/reksadana/RD562/bri-indeks-syariah",
    "https://bibit.id/reksadana/RD424/bnp-paribas-pesona-syariah"
]

# Periode Analisa (Sesuai strategi kita sebelumnya)
PERIODE_ANALISA = "3M" 
# =========================================================

def print_log(msg):
    print(msg)
    sys.stdout.flush()

def kirim_telegram(pesan):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print_log("❌ Error: Token/Chat ID belum disetting di GitHub Secrets!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print_log(f"❌ Gagal Kirim Telegram: {e}")

def scrape_bibit(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200: return None

        soup = BeautifulSoup(response.text, 'html.parser')
        script_data = soup.find('script', id='__NEXT_DATA__')
        if not script_data: return None

        json_data = json.loads(script_data.string)
        product = json_data.get('props', {}).get('pageProps', {}).get('productDetail')

        if product:
            nama = product.get('name', 'Reksadana')
            nav = product.get('nav', {})
            harga_sekarang = float(nav.get('value', 0))
            
            changes = product.get('changesvalue', {})
            chg_1d = float(changes.get('1d', 0))
            ret_1m = float(changes.get('1m', 0))
            ret_1y = float(changes.get('1y', 0))
            
            # Rumus Reverse Percentage (Harga Lalu)
            harga_lalu_1m = harga_sekarang / (1 + (ret_1m / 100))
            harga_lalu_1y = harga_sekarang / (1 + (ret_1y / 100))

            # Status Analisa
            status_beli = "Wait & See"
            if ret_1m <= -2.0:
                status_beli = "🔥 SUPER DISKON (Murah Banget)"
            elif ret_1m < 0:
                status_beli = "✅ Diskon (Lebih murah dari bulan lalu)"
            else:
                status_beli = "⚠️ Harga Sedang Tinggi"

            return {
                'nama': nama,
                'harga': harga_sekarang,
                'chg_rp': chg_1d,
                'chg_pct': (chg_1d / (harga_sekarang - chg_1d) * 100) if (harga_sekarang - chg_1d) > 0 else 0,
                'ret_1m': ret_1m,
                'ret_1y': ret_1y,
                'harga_lalu_1m': harga_lalu_1m,
                'harga_lalu_1y': harga_lalu_1y,
                'status': status_beli
            }
    except Exception as e:
        print_log(f"Error Scrape {url}: {e}")
    return None

def job_cek_portofolio():
    # Set Timezone Jakarta/Makassar untuk Laporan
    tz = pytz.timezone('Asia/Makassar') 
    waktu = datetime.now(tz).strftime('%d-%m-%Y %H:%M')
    print_log(f"🚀 MULAI CEK: {waktu} WITA")
    
    laporan = []
    for url in WATCHLIST:
        print_log(f"🔎 Sedang cek: {url} ...")
        data = scrape_bibit(url)
        if data:
            icon = "🚀" if data['chg_rp'] > 0 else ("🔻" if data['chg_rp'] < 0 else "➖")
            pesan = (
                f"{icon} *{data['nama']}*\n"
                f"Harga Skrg: *Rp {data['harga']:,.0f}*\n"
                f"Harian: {data['chg_pct']:+.2f}% (Rp {data['chg_rp']:,.0f})\n"
                f"------------------------\n"
                f"📅 *Perbandingan Harga*:\n"
                f"vs 1 Bulan Lalu: Rp {data['harga_lalu_1m']:,.0f} ({data['ret_1m']:+.2f}%)\n"
                f"vs 1 Tahun Lalu: Rp {data['harga_lalu_1y']:,.0f} ({data['ret_1y']:+.2f}%)\n"
                f"💡 Status: *{data['status']}*"
            )
            laporan.append(pesan)

    if laporan:
        head = f"📊 *LAPORAN HARIAN*\n📅 {waktu}\n"
        foot = "\n------------------------\n🤖 *PantauSaham Bot (GitHub Actions)*"
        kirim_telegram(head + "\n".join(laporan) + foot)
        print_log("✅ Laporan Terkirim!")
    else:
        print_log("❌ Data kosong.")

# ================= MAIN PROGRAM =================
if __name__ == "__main__":
    # Langsung jalankan sekali, lalu mati (Selesai)
    print("🤖 Ninja Bot Beraksi...")
    job_cek_portofolio()
    print("✅ Tugas Selesai.")