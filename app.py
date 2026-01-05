import streamlit as st
import pandas as pd
import requests
import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Meme-Watch Pro + Telegram", layout="wide", page_icon="🎯")

# --- 2. FUNGSI TELEGRAM BOT ---
def send_telegram_msg(token, chat_id, message):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
            requests.post(url, json=payload)
        except Exception as e:
            st.sidebar.error(f"Telegram Error: {e}")

# --- 3. LOGIC SIGNAL & SCORING ---
def get_trade_signal(row_data):
    try:
        change_24h = float(row_data['change_raw'])
        vol = float(row_data['vol_raw'])
        liq = float(row_data['liq_raw'])
        
        score = 50
        if vol > liq: score += 20
        if liq > 1500000: score += 20
        
        if -15 <= change_24h <= -5 and vol > (liq * 1.5):
            return "🟢 BUY: AKUMULASI", "Strong Buy", min(score, 100)
        elif change_24h > 50:
            return "🔴 SELL: TAKE PROFIT", "Danger Zone", score
        elif -5 < change_24h < 15:
            return "🟡 HOLD: KONSOLIDASI", "Neutral", score
        else:
            return "⚪ WAIT: VOLATILITAS", "Observing", score
    except:
        return "❓ DATA ERROR", "N/A", 0

# --- 4. FETCH DATA ---
@st.cache_data(ttl=60)
def fetch_crypto_data(symbols):
    results = []
    for sym in symbols:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={sym}"
            res = requests.get(url, timeout=10).json()
            pairs = res.get('pairs', [])
            if pairs:
                best_pair = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0))
                raw_data = {
                    "change_raw": best_pair.get('priceChange', {}).get('h24', 0),
                    "vol_raw": best_pair.get('volume', {}).get('h24', 0),
                    "liq_raw": best_pair.get('liquidity', {}).get('usd', 0)
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
                    "Link": best_pair['url']
                })
        except: continue
    return results

# --- 5. SIDEBAR: CONFIG & TELEGRAM ---
st.sidebar.header("🤖 Telegram Alert Bot")
tg_token = st.sidebar.text_input("Bot Token", type="password", help="Dapatkan dari @BotFather")
tg_chat_id = st.sidebar.text_input("Chat ID", help="Dapatkan dari @userinfobot")

if st.sidebar.button("🔄 Force Refresh & Scan"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.info("Tips: Bot akan otomatis mengirim pesan hanya jika ada signal 'Strong Buy' atau 'Danger Zone'.")

# --- 6. MAIN UI ---
st.title("🎯 Meme-Watch Pro 2026")
st.subheader(f"Live Monitor: {datetime.datetime.now().strftime('%H:%M:%S')}")

target_coins = ["PIPPIN", "GOAT", "PENGU", "SPX6900", "FARTCOIN", "POPCAT", "PNUT", "BRETT", "MOODENG"]
data_list = fetch_crypto_data(target_coins)

if data_list:
    df = pd.DataFrame(data_list)
    
    # --- PROSES SIGNAL ALERT ---
    priority_df = df[df['Status'].isin(['Strong Buy', 'Danger Zone'])]
    
    if not priority_df.empty:
        st.header("🚀 High Priority Signals")
        cols = st.columns(len(priority_df))
        
        for i, (_, row) in enumerate(priority_df.iterrows()):
            # Visual di Streamlit
            with cols[i]:
                st.metric(label=row['Koin'], value=row['Harga'], delta=row['Perubahan 24h'])
                st.info(f"Signal: {row['Signal']}")
            
            # Kirim Notifikasi Telegram
            alert_msg = (
                f"🚨 *MEME SIGNAL DETECTED!*\n\n"
                f"Token: {row['Koin']}\n"
                f"Price: {row['Harga']}\n"
                f"24h Change: {row['Perubahan 24h']}\n"
                f"Signal: {row['Signal']}\n"
                f"Score: {row['Score']}%\n\n"
                f"[Link DexScreener]({row['Link']})"
            )
            send_telegram_msg(tg_token, tg_chat_id, alert_msg)
    else:
        st.info("Market cenderung sideways. Belum ada signal ekstrim.")

    st.divider()

    # --- DATAFRAME VIEW ---
    st.header("📋 Market Overview")
    st.dataframe(
        df[['Koin', 'Score', 'Signal', 'Harga', 'Perubahan 24h', 'Volume', 'Likuiditas']],
        use_container_width=True, hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn("Trust Score", min_value=0, max_value=100)
        }
    )

    # --- AUDIT TOOLS ---
    st.subheader("🛡️ Safety Audit")
    t1, t2 = st.columns(2)
    for i, row in df.iterrows():
        col = t1 if i % 2 == 0 else t2
        with col.expander(f"Audit {row['Koin']}"):
            st.write(f"CA: `{row['CA']}`")
            st.markdown(f"[RugCheck](https://www.rugcheck.xyz/mainnet/token/{row['CA']}) | [BubbleMaps](https://bubblemaps.io/token/{row['CA']})")

st.caption("Disclaimer: Not financial advice. Always DYOR.")
