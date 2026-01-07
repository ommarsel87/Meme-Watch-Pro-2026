import streamlit as st
import pandas as pd
import requests
import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Meme-Watch Pro Multi-Chain", layout="wide", page_icon="🎯")

# --- FUNGSI SUARA (AUDIO ALERT) ---
def play_sound():
    audio_html = """
        <audio autoplay>
            <source src="https://files.catbox.moe/97v977.mp3" type="audio/mp3">
        </audio>
    """
    st.components.v1.html(audio_html, height=0, width=0)

# --- 2. FUNGSI TELEGRAM BOT ---
def send_telegram_msg(token, chat_id, message):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            st.sidebar.error(f"Telegram Error: {e}")

# --- 3. LOGIC SIGNAL & SCORING ---
def get_trade_signal(row_data):
    try:
        change_24h = float(row_data['change_raw'])
        vol = float(row_data['vol_raw'])
        liq = float(row_data['liq_raw'])
        
        score = 50
        if vol > (liq * 0.4): score += 15
        if liq > 1000000: score += 20
        
        if -20 <= change_24h <= -5 and vol > (liq * 1.1):
            return "🟢 BUY: DIP AKUMULASI", "Strong Buy", min(score + 15, 100)
        elif change_24h > 45:
            return "🔴 SELL: OVERBOUGHT", "Danger Zone", score
        elif -5 < change_24h < 15:
            return "🟡 HOLD: KONSOLIDASI", "Neutral", score
        else:
            return "⚪ WAIT: OBSERVASI", "Observing", score
    except:
        return "❓ DATA ERROR", "N/A", 0

# --- 4. FETCH DATA DENGAN FILTER CHAIN ---
@st.cache_data(ttl=60)
def fetch_meme_data(symbols, selected_chain):
    results = []
    for sym in symbols:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={sym}"
            res = requests.get(url, timeout=10).json()
            pairs = res.get('pairs', [])
            
            if pairs:
                # Jika filter chain aktif, saring hanya chain yang dipilih
                if selected_chain != "All":
                    pairs = [p for p in pairs if p['chainId'].lower() == selected_chain.lower()]
                
                if not pairs: continue

                best_pair = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0))
                liq_usd = best_pair.get('liquidity', {}).get('usd', 0)
                
                # Filter likuiditas > 1M
                if liq_usd >= 1000000:
                    raw_data = {
                        "change_raw": best_pair.get('priceChange', {}).get('h24', 0),
                        "vol_raw": best_pair.get('volume', {}).get('h24', 0),
                        "liq_raw": liq_usd
                    }
                    signal, status_label, score = get_trade_signal(raw_data)
                    results.append({
                        "Koin": best_pair['baseToken']['symbol'],
                        "Harga": f"${float(best_pair['priceUsd']):.6f}",
                        "Perubahan 24h": f"{raw_data['change_raw']}%",
                        "Volume": f"${raw_data['vol_raw']:,.0f}",
                        "Likuiditas": f"${raw_data['liq_raw']:,.0f}",
                        "Score": score,
                        "Signal": signal,
                        "Status": status_label,
                        "CA": best_pair['baseToken']['address'],
                        "Link": best_pair['url'],
                        "Chain": best_pair['chainId'].upper()
                    })
        except: continue
    return results

# --- 5. SIDEBAR: FILTER & CONFIG ---
st.sidebar.header("⚙️ Filter & Monitoring")
# Fitur Filter Khusus Jaringan
chain_option = st.sidebar.selectbox(
    "Pilih Jaringan (Chain):",
    ["All", "Solana", "Ethereum", "BSC", "Base", "Arbitrum"]
)

enable_sound = st.sidebar.checkbox("Aktifkan Sound Alert 🔊", value=True)

st.sidebar.divider()
st.sidebar.subheader("🤖 Telegram Bot")
tg_token = st.sidebar.text_input("Bot Token", type="password")
tg_chat_id = st.sidebar.text_input("Chat ID")

if st.sidebar.button("🔄 Update Manual"):
    st.cache_data.clear()
    st.rerun()

# --- 6. MAIN UI ---
st.title("🎯 Meme-Watch Pro 2026")
st.write(f"Jaringan: **{chain_option}** | Jam: **{datetime.datetime.now().strftime('%H:%M:%S')}**")

# Daftar 10 Koin Meme Target
target_coins = ["PIPPIN", "TRUMP", "PENGU", "SPX", "FARTCOIN", "MOG", "POPCAT", "PNUT", "MOODENG", "GOAT"]
data_list = fetch_meme_data(target_coins, chain_option)

if data_list:
    df = pd.DataFrame(data_list)
    
    # Logic Signal & Sound
    priority_df = df[df['Status'] == 'Strong Buy']
    if not priority_df.empty:
        if enable_sound:
            play_sound()
            st.toast("🚨 SINYAL BELI TERDETEKSI!", icon="🔥")
        
        st.header("🚀 High Priority Signals")
        cols = st.columns(len(priority_df))
        for i, (_, row) in enumerate(priority_df.iterrows()):
            with cols[i]:
                st.metric(label=row['Koin'], value=row['Harga'], delta=row['Perubahan 24h'])
                st.success(f"Signal: {row['Signal']}")

    st.divider()

    # Data Table
    st.header(f"📋 Market Data ({chain_option})")
    st.dataframe(
        df[['Koin', 'Chain', 'Score', 'Signal', 'Harga', 'Perubahan 24h', 'Volume', 'Likuiditas']],
        use_container_width=True, hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn("Trust Score", min_value=0, max_value=100)
        }
    )

    # Security Check
    with st.expander("🛡️ Smart Contract Audit Tools"):
        for _, row in df.iterrows():
            c1, c2 = st.columns([1, 3])
            c1.write(f"**{row['Koin']}** ({row['Chain']})")
            c2.code(row['CA'], language="text")
            st.markdown(f"[RugCheck](https://www.rugcheck.xyz/mainnet/token/{row['CA']}) | [DEXTools](https://www.dextools.io/app/en/{row['Chain'].lower()}/pair-explorer/{row['CA']})")
            st.divider()
else:
    st.warning(f"Tidak ada koin dari list 10 besar yang ditemukan di jaringan **{chain_option}** dengan likuiditas > $1M.")

st.caption("Klik di mana saja pada layar ini agar fitur Sound Alert aktif saat data terupdate.")
