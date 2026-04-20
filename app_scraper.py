import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import time
import sys
import re

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

st.set_page_config(page_title="Data Mining Scraper Pro", layout="wide")
st.title("🚀 AI Multi-Platform Scraper Dashboard")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Konfigurasi")
    platform = st.selectbox("Pilih Platform", ["X (Twitter)", "Google Maps", "Facebook"])
    
    maps_mode = ""
    lokasi = ""
    if platform == "Google Maps":
        maps_mode = st.selectbox("Tujuan Scraping Maps", ["Cari Tempat", "Cari Ulasan Spesifik"])
    
    if platform == "Google Maps" and maps_mode == "Cari Ulasan Spesifik":
        target_url = st.text_input("URL Google Maps Target", placeholder="Tempel link ulasan di sini...")
        keyword = st.text_input("Keyword Filter (Opsional)", placeholder="Contoh: jelek")
        lokasi = ""
    else:
        keyword = st.text_input("Keyword / Nama Tempat", placeholder="Contoh: mbg")
        if platform == "Google Maps":
            lokasi = st.text_input("Daerah/Lokasi", placeholder="Contoh: Bekasi")
        else:
            lokasi = ""
        target_url = None

    limit = st.number_input("Target Data Maksimal", min_value=1, max_value=1000, value=50)
    st.divider()
    run_button = st.button("MULAI SCRAPING", use_container_width=True, type="primary")

async def scrape_engine(keyword, limit, platform, maps_mode, target_url, lokasi):
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            await page.bring_to_front()

            if platform == "Google Maps":
                if maps_mode == "Cari Ulasan Spesifik" and target_url:
                    await page.goto(target_url)
                    await asyncio.sleep(5)
                    try:
                        btns = await page.query_selector_all('button[aria-label*="Ulasan"], button[aria-label*="Reviews"]')
                        for b in btns:
                            if await b.is_visible():
                                await b.click()
                                await asyncio.sleep(3)
                                break
                    except: pass
                else:
                    q = f"{keyword} {lokasi}".strip()
                    await page.goto(f"https://www.google.com/maps/search/{q.replace(' ', '+')}")
                    await asyncio.sleep(5)

            results = []
            seen_content = set()
            bar = st.progress(0)
            status = st.empty()
            preview = st.empty()
            stuck_counter = 0
            
            while len(results) < limit:
                if page.is_closed(): break
                jumlah_sebelumnya = len(results)
                
                if platform == "X (Twitter)":
                    # MENGGUNAKAN LOGIKA main_scraper.py YANG SUDAH BERHASIL
                    await page.mouse.wheel(0, 1500)
                    await asyncio.sleep(2.5)
                    
                    articles = await page.query_selector_all('article')
                    for article in articles:
                        if len(results) >= limit: break
                        text_element = await article.query_selector('div[data-testid="tweetText"]')
                        if text_element:
                            content = await text_element.inner_text()
                            cln = content.replace('\n', ' ').strip()
                            if cln and cln not in seen_content:
                                if not keyword or keyword.lower() in cln.lower():
                                    results.append({'waktu': time.strftime("%H:%M:%S"), 'content': cln, 'platform': 'X'})
                                    seen_content.add(cln)

                elif platform == "Google Maps" and maps_mode == "Cari Tempat":
                    await page.mouse.move(200, 500)
                    await page.mouse.wheel(0, 2000)
                    await asyncio.sleep(3)
                    cards = await page.query_selector_all('div[role="article"], a.hf79be')
                    for c in cards:
                        if len(results) >= limit: break
                        nm_el = await c.query_selector('div.qBF1Pd, div.fontHeadlineSmall')
                        st_el = await c.query_selector('span.MW4etd, [aria-label*="bintang"]')
                        txt_all = await c.inner_text()
                        ph = re.search(r'(\+62|0\d{1,3})[-\s]?\(?\d{2,4}?\)?[-.\s]?\d{3,4}[-.\s]?\d{3,5}', txt_all)
                        if nm_el:
                            nm = await nm_el.inner_text()
                            if nm not in seen_content:
                                results.append({
                                    'waktu': time.strftime("%H:%M:%S"),
                                    'nama': nm,
                                    'bintang': await st_el.inner_text() if st_el else "0",
                                    'no_telp': ph.group(0) if ph else "N/A",
                                    'content': nm,
                                    'platform': 'Maps'
                                })
                                seen_content.add(nm)

                elif platform == "Google Maps" and maps_mode == "Cari Ulasan Spesifik":
                    await page.mouse.move(400, 600)
                    await page.mouse.click(400, 600)
                    await page.mouse.wheel(0, 3000)
                    await asyncio.sleep(3)
                    revs = await page.query_selector_all('div.jftiEf')
                    for r in revs:
                        if len(results) >= limit: break
                        t_el = await r.query_selector('span.wiI7pd')
                        s_el = await r.query_selector('span.kvMY9b, [aria-label*="bintang"]')
                        if t_el:
                            con = await t_el.inner_text()
                            cln = con.replace('\n', ' ').strip()
                            if cln and cln not in seen_content:
                                s_raw = await s_el.get_attribute('aria-label') if s_el else "0"
                                bnt = re.findall(r'\d+', s_raw)[0] if s_raw else "0"
                                if not keyword or keyword.lower() in cln.lower():
                                    results.append({'waktu': time.strftime("%H:%M:%S"), 'content': cln, 'bintang': bnt, 'platform': 'Maps'})
                                    seen_content.add(cln)

                if len(results) == jumlah_sebelumnya:
                    stuck_counter += 1
                else:
                    stuck_counter = 0
                
                if stuck_counter >= 3: # Berhenti jika 3x scroll tidak ada data baru (Sesuai main_scraper.py)
                    break
                
                bar.progress(min(len(results) / limit, 1.0))
                status.info(f"📊 Progress: {len(results)} data ditangkap...")
                if results:
                    preview.table(pd.DataFrame(results).tail(3))

            return pd.DataFrame(results), f"hasil_{keyword}.csv"
        except Exception as e:
            st.error(f"Error: {e}")
            return None, None

if run_button:
    if keyword or target_url:
        d, f = asyncio.run(scrape_engine(keyword, limit, platform, maps_mode, target_url, lokasi))
        if d is not None and not d.empty:
            st.success(f"🔥 Selesai! Berhasil ambil {len(d)} data unik.")
            st.download_button("💾 DOWNLOAD CSV", d.to_csv(index=False), f, "text/csv")
            st.dataframe(d, use_container_width=True)
        else:
            st.warning("⚠️ Data 0. Pastikan tab target aktif dan Chrome Debugging menyala!")