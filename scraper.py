import asyncio, urllib.parse, re, threading
from playwright.async_api import async_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

DORKS = {
    "linkedin":  'site:linkedin.com/in/ "{query}"',
    "instagram": 'site:instagram.com "{query}"',
    "facebook":  'site:facebook.com "{query}"',
    "twitter":   'site:twitter.com "{query}" OR site:x.com "{query}"',
    "vk":        'site:vk.com "{query}"',
}

CAPTCHA_SELECTORS = [
    'iframe[src*="recaptcha"]', 'iframe[src*="captcha"]',
    '.g-recaptcha', 'input[name="captcha"]', '[class*="captcha"]',
    '#challenge-form', 'form[action*="captcha"]', 'div[id*="challenge"]',
]
BLOCKED_IMG = [
    "bing.com","microsoft.com","gstatic.com/images/icons",
    "google.com/images/branding","googlelogo","1x1","pixel.gif",
    "blank.gif","spacer","logo_","msn.com","schemas.microsoft",
]

# ── Helpers ───────────────────────────────────────────────────────────────────
async def _txt(el, sel):
    try:
        n = await el.query_selector(sel)
        return (await n.inner_text()).strip() if n else ""
    except: return ""

async def _attr(el, sel, attr):
    try:
        n = await el.query_selector(sel)
        return (await n.get_attribute(attr) or "").strip() if n else ""
    except: return ""

async def _accept_cookies(page):
    for t in ["Tout accepter","Accept all","Accepter","J'accepte","Agree","I agree","Accept"]:
        try:
            btn = page.locator(f"button:has-text('{t}')")
            if await btn.count() > 0:
                await btn.first.click(timeout=2500)
                await page.wait_for_timeout(500)
                return
        except: pass

async def _has_captcha(page):
    for sel in CAPTCHA_SELECTORS:
        try:
            if await page.query_selector(sel): return True
        except: pass
    try:
        title = (await page.title()).lower()
        if any(k in title for k in ["captcha","challenge","robot","verify","unusual"]):
            return True
        # Google reCAPTCHA page détection
        content = await page.inner_text("body")
        if "unusual traffic" in content.lower() or "not a robot" in content.lower():
            return True
    except: pass
    return False

async def _wait_captcha_solve(page, on_event, captcha_event: threading.Event, category):
    await page.bring_to_front()
    on_event({"type": "captcha", "category": category, "url": page.url})
    print(f"⚠️  CAPTCHA sur {category} — résolvez dans la fenêtre.")
    for _ in range(1200):   # 120s max
        if captcha_event.is_set():
            captcha_event.clear(); break
        try:
            if await page.query_selector("div.g, div.MjjYud, div.result, li.b_algo, .gsc-result"):
                break
        except: pass
        await asyncio.sleep(0.1)
    on_event({"type": "captcha_solved", "category": category})
    await page.wait_for_timeout(800)

def _ok_img(src):
    if not src or src.startswith("data:") or len(src) < 15: return False
    return not any(b in src for b in BLOCKED_IMG)

def _decode_ddg(raw):
    if not raw: return ""
    if "uddg=" in raw:
        try: return urllib.parse.unquote(raw.split("uddg=")[1].split("&")[0])
        except: pass
    return raw if raw.startswith("http") else ""

# ── GOOGLE dork — résultats texte ─────────────────────────────────────────────
async def _extract_google(page, category):
    results = []
    # Stratégie 1 : conteneurs div.g / MjjYud / tF2Cxc
    for c in await page.query_selector_all("div.g, div.MjjYud, div.tF2Cxc, div[data-sokoban-container]"):
        try:
            title = await _txt(c, "h3")
            if not title: continue
            href = await c.evaluate(
                "el => { const a = el.querySelector('a[href]'); return a ? a.href : ''; }"
            )
            if not href or "google" in href or href.startswith("/"): continue
            snippet = await _txt(c, "div.VwiC3b, span.aCOpRe, div[data-sncf], div.ITZIwc")
            results.append({"title": title, "url": href, "snippet": snippet, "category": category})
        except: continue
    # Stratégie 2 : fallback h3
    if not results:
        for h3 in await page.query_selector_all("h3"):
            try:
                title = (await h3.inner_text()).strip()
                if not title or len(title) < 4: continue
                href = await h3.evaluate(
                    "el => { const a = el.closest('a') || el.parentElement?.querySelector('a'); return a ? a.href : ''; }"
                )
                if not href or "google" in href or href.startswith("/"): continue
                results.append({"title": title, "url": href, "snippet": "", "category": category})
            except: continue
    return results[:8]

async def google_dork(page, raw_query, category, on_event, captcha_event):
    results = []
    q   = urllib.parse.quote_plus(raw_query)
    url = f"https://www.google.fr/search?q={q}&hl=fr&num=10&gl=fr"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(1500)
        await _accept_cookies(page)
        await page.wait_for_timeout(400)
        if await _has_captcha(page):
            await _wait_captcha_solve(page, on_event, captcha_event, category)
        results = await _extract_google(page, category)
        # Fallback DDG si Google retourne toujours 0
        if not results:
            print(f"[{category.upper()}] Google vide → fallback DDG")
            q2  = urllib.parse.quote_plus(raw_query)
            url2 = f"https://html.duckduckgo.com/html/?q={q2}&kl=fr-fr"
            await page.goto(url2, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(1000)
            for item in (await page.query_selector_all("div.result"))[:8]:
                try:
                    title    = await _txt(item, "a.result__a")
                    raw_href = await _attr(item, "a.result__a", "href")
                    href     = _decode_ddg(raw_href)
                    snippet  = await _txt(item, "a.result__snippet")
                    if title and href:
                        results.append({"title": title, "url": href, "snippet": snippet, "category": category})
                except: continue
    except Exception as e:
        print(f"[GOOGLE DORK ERROR] {category}: {e}")
    return results

# ── GOOGLE Images (50 max) ─────────────────────────────────────────────────────
async def google_images(page, query, on_event, captcha_event):
    images, seen = [], set()
    q   = urllib.parse.quote_plus(query)
    url = f"https://www.google.fr/search?q={q}&tbm=isch&hl=fr&gl=fr"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2000)
        await _accept_cookies(page)
        if await _has_captcha(page):
            await _wait_captcha_solve(page, on_event, captcha_event, "images_google")
        # Scroll x5
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, 1800)")
            await page.wait_for_timeout(600)
        # Sélecteurs images Google réelles (div.islrc = conteneur résultats d'images)
        for img in await page.query_selector_all("div.islrc img, img.Q4LuWd, img.rg_i, div[jsname='dTDiAc'] img"):
            try:
                src = (await img.get_attribute("src") or await img.get_attribute("data-src") or "")
                if not _ok_img(src) or src in seen: continue
                seen.add(src)
                alt    = (await img.get_attribute("alt") or "").strip()
                source = await img.evaluate("el => { const a = el.closest('a'); return a ? a.href : ''; }")
                images.append({"src": src, "alt": alt,
                                "filename": src.split("/")[-1].split("?")[0],
                                "source_url": source, "engine": "google"})
                if len(images) >= 50: break
            except: continue
    except Exception as e:
        print(f"[GOOGLE IMAGES ERROR]: {e}")
    return images

# ── BING Images (50 max) ──────────────────────────────────────────────────────
async def bing_images(page, query, on_event, captcha_event):
    images, seen = [], set()
    q   = urllib.parse.quote_plus(query)
    url = f"https://www.bing.com/images/search?q={q}&first=1&count=50&mkt=fr-FR"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2000)
        await _accept_cookies(page)
        if await _has_captcha(page):
            await _wait_captcha_solve(page, on_event, captcha_event, "images_bing")
        for _ in range(6):
            await page.evaluate("window.scrollBy(0, 2000)")
            await page.wait_for_timeout(600)
        for img in await page.query_selector_all("img.mimg, .iusc img, div.imgpt img"):
            try:
                src = (await img.get_attribute("src") or await img.get_attribute("data-src") or "")
                if not _ok_img(src) or src in seen: continue
                seen.add(src)
                alt    = (await img.get_attribute("alt") or "").strip()
                source = await img.evaluate("el => { const a = el.closest('a'); return a ? a.href : ''; }")
                images.append({"src": src, "alt": alt,
                                "filename": src.split("/")[-1].split("?")[0],
                                "source_url": source, "engine": "bing"})
                if len(images) >= 50: break
            except: continue
        # Fallback data-m JSON (HD URLs)
        if len(images) < 20:
            for card in await page.query_selector_all(".iusc[m], div[m], a[m]"):
                try:
                    m_attr = await card.get_attribute("m") or ""
                    match  = re.search(r'"murl"\s*:\s*"([^"]+)"', m_attr)
                    if not match: continue
                    src = match.group(1)
                    if not _ok_img(src) or src in seen: continue
                    seen.add(src)
                    alt_m = re.search(r'"t"\s*:\s*"([^"]+)"', m_attr)
                    images.append({"src": src, "alt": alt_m.group(1) if alt_m else "",
                                   "filename": src.split("/")[-1].split("?")[0],
                                   "source_url": "", "engine": "bing"})
                    if len(images) >= 50: break
                except: continue
    except Exception as e:
        print(f"[BING IMAGES ERROR]: {e}")
    return images

# ── Images combinées Google + Bing (100 max) ──────────────────────────────────
async def combined_images(page, query, on_event, captcha_event):
    all_imgs, seen = [], set()

    on_event({"type": "log", "msg": "🖼️ Images Google…"})
    g_imgs = await google_images(page, query, on_event, captcha_event)
    for img in g_imgs:
        if img["src"] not in seen:
            seen.add(img["src"]); all_imgs.append(img)
    print(f"[IMAGES] Google: {len(g_imgs)}")

    await asyncio.sleep(0.8)

    on_event({"type": "log", "msg": "🖼️ Images Bing…"})
    b_imgs = await bing_images(page, query, on_event, captcha_event)
    for img in b_imgs:
        if img["src"] not in seen:
            seen.add(img["src"]); all_imgs.append(img)
    print(f"[IMAGES] Bing: {len(b_imgs)} | Total unique: {len(all_imgs)}")

    return all_imgs  # jusqu'à ~100

# ── Whitepages multi-pages ────────────────────────────────────────────────────
async def _extract_wp_page(page):
    results = []
    for item in await page.query_selector_all(".gsc-result, .gs-result"):
        try:
            title   = await _txt(item, ".gs-title a, .gs-title, h3")
            href    = await _attr(item, ".gs-title a, a[href]", "href")
            snippet = await _txt(item, ".gs-snippet, .gsc-description, p")
            if not title: continue
            if "google.com/url" in href:
                m = re.search(r"[?&]q=([^&]+)", href)
                if m: href = urllib.parse.unquote(m.group(1))
            results.append({"title": title, "url": href or "", "snippet": snippet, "category": "whitepages"})
        except: continue
    if not results:
        for c in await page.query_selector_all("div.g, div.MjjYud, div.tF2Cxc"):
            try:
                title = await _txt(c, "h3")
                if not title: continue
                href = await c.evaluate("el => { const a = el.querySelector('a[href]'); return a ? a.href : ''; }")
                if not href or "google" in href or href.startswith("/"): continue
                snippet = await _txt(c, "div.VwiC3b, span.aCOpRe, div[data-sncf]")
                results.append({"title": title, "url": href, "snippet": snippet, "category": "whitepages"})
            except: continue
    if not results:
        for h3 in await page.query_selector_all("h3"):
            try:
                title = (await h3.inner_text()).strip()
                if not title or len(title) < 4: continue
                href = await h3.evaluate(
                    "el => { const a = el.closest('a') || el.parentElement?.closest('a'); return a ? a.href : ''; }"
                )
                if not href or href.startswith("/") or "google" in href: continue
                results.append({"title": title, "url": href, "snippet": "", "category": "whitepages"})
            except: continue
    return results

async def whitepages_search(page, query, on_event, captcha_event, max_pages=5):
    all_results, seen_urls = [], set()
    q = urllib.parse.quote_plus(query)
    try:
        await page.goto(f"https://whitepages.fr/?q={q}", wait_until="domcontentloaded", timeout=25000)
        await _accept_cookies(page)
        if await _has_captcha(page):
            await _wait_captcha_solve(page, on_event, captcha_event, "whitepages")
        try:
            await page.wait_for_selector(".gsc-result,.gs-result,div.g,div.MjjYud,h3", timeout=12000)
        except: await page.wait_for_timeout(5000)

        for pg in range(1, max_pages + 1):
            if pg > 1:
                try:
                    btn = page.locator(f".gsc-cursor-page:has-text('{pg}')")
                    if await btn.count() == 0:
                        btn = page.locator("td.gsc-cursor-next-page,button:has-text('Suivant'),a:has-text('Suivant')")
                        if await btn.count() == 0: break
                    await btn.first.click()
                    await page.wait_for_timeout(2500)
                    await page.wait_for_function(
                        "() => document.querySelectorAll('.gsc-result,div.g,h3').length > 0", timeout=8000
                    )
                except Exception as e:
                    print(f"[WP] page {pg}: {e}"); break
            page_r = await _extract_wp_page(page)
            new = sum(1 for r in page_r if r["url"] not in seen_urls)
            for r in page_r:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"]); all_results.append(r)
            print(f"[WHITEPAGES] Page {pg}: {len(page_r)} ({new} nouveaux)")
            if pg > 1 and new == 0: break
            await asyncio.sleep(0.8)

        for a_el in await page.query_selector_all("a"):
            try:
                text = (await a_el.inner_text()).strip()
                href = await a_el.get_attribute("href") or ""
                kw = ["press","gov","archive","presse","journal","tribunal","bodacc","infogreffe"]
                if any(k in text.lower() or k in href.lower() for k in kw) and href and href not in seen_urls:
                    seen_urls.add(href)
                    full = href if href.startswith("http") else "https://whitepages.fr" + href
                    all_results.append({"title": text or href, "url": full,
                                        "snippet": "📁 Section avancée", "category": "whitepages"})
            except: pass
    except Exception as e:
        print(f"[WHITEPAGES ERROR]: {e}")
    print(f"[WHITEPAGES] Total: {len(all_results)} uniques")
    return all_results

# ── Entry point ───────────────────────────────────────────────────────────────
async def run_search(query, on_event, captcha_event: threading.Event):
    data = {k: [] for k in ["linkedin","instagram","facebook","twitter","vk","whitepages","images"]}

    async with async_playwright() as pw:
        browser = None
        launch_kw = dict(
            headless=False,
            args=["--no-sandbox","--disable-blink-features=AutomationControlled",
                  "--window-position=40,40","--window-size=1200,700"]
        )
        for channel in ["msedge", "chrome", None]:
            try:
                browser = await pw.chromium.launch(
                    **({"channel": channel, **launch_kw} if channel else launch_kw)
                )
                print(f"[BROWSER] {channel or 'Playwright Chromium'}")
                break
            except Exception as e:
                print(f"[BROWSER] {channel or 'chromium'} indisponible: {e}")

        if not browser:
            on_event({"type":"complete","data":data,
                      "error":"Aucun navigateur. Lance: playwright install chromium"})
            return data

        ctx = await browser.new_context(
            user_agent=UA, locale="fr-FR", viewport={"width":1200,"height":700},
            extra_http_headers={"Accept-Language":"fr-FR,fr;q=0.9,en;q=0.8"}
        )
        await ctx.add_init_script("""
            Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
            Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
            Object.defineProperty(navigator,'languages',{get:()=>['fr-FR','fr','en']});
            window.chrome={runtime:{}};
        """)
        page = await ctx.new_page()

        # ── Réseaux sociaux → GOOGLE avec fallback DDG ────────────────────────
        print("[*] Moteur principal : Google.fr (headless=False)")
        for cat, template in DORKS.items():
            on_event({"type":"scanning","category":cat})
            dork      = template.replace("{query}", query)
            data[cat] = await google_dork(page, dork, cat, on_event, captcha_event)
            on_event({"type":"cat_done","category":cat,"count":len(data[cat]),"results":data[cat]})
            print(f"[{cat.upper()}] {len(data[cat])} résultats")
            await asyncio.sleep(1.2)

        # ── Images → Google + Bing combinés ───────────────────────────────────
        on_event({"type":"scanning","category":"images"})
        data["images"] = await combined_images(page, query, on_event, captcha_event)
        on_event({"type":"cat_done","category":"images","count":len(data["images"]),"results":data["images"]})
        await asyncio.sleep(1.0)

        # ── Whitepages ────────────────────────────────────────────────────────
        on_event({"type":"scanning","category":"whitepages"})
        data["whitepages"] = await whitepages_search(page, query, on_event, captcha_event)
        on_event({"type":"cat_done","category":"whitepages","count":len(data["whitepages"]),"results":data["whitepages"]})

        await browser.close()

    on_event({"type":"complete","data":data})
    return data