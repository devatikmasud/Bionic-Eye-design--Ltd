from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import unquote
import json
import re
import socket
import subprocess
import time

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
EXPECTED_NAV = ["Home", "Solutions", "Support", "Regulation", "Sectors", "About Us", "Contact", "Shop"]
EXPECTED_SOURCE_VIDEOS = {
    "5f69a5e2-edb9-4dff-8bd8-14d3a8d570d0.MP4",
    "ABZ Clean Station_ Full Setup & Operation Guide (2).mp4",
    "C10 Academy.mp4",
    "C10 Short Low bitrate.mp4",
    "C10-Use-Case-Shorts-Final-Horizontal.mp4",
    "C10_Introduction_short.mp4",
}
EXPECTED_APPLICATIONS = [
    "Commercial and residential facades, and glass curtain walling",
    "Solar farms and rooftop arrays",
    "Wind turbine towers",
    "Industrial silos, tanks and cladding",
    "Heritage and listed structures",
    "Graffiti removal",
    "Surface coating and treatment, currently in development",
]
EXPECTED_COPY = [
    "Facade and structure cleaning without access equipment.",
    "Drone cleaning removes the requirement for scaffolding, cradles, powered access or rope teams across a substantial proportion of facade, glazing, cladding and roof maintenance. The work is carried out from ground level, and setup is measured in minutes rather than days.",
    "It does not replace access equipment for every application. We identify where it does not before specifying a system.",
    "The ABZ Innovation C10 is the platform we have standardised on. It operates to over 60 metres, delivers up to 15 litres per minute at a working pressure around 170 bar at the nozzle, up to 255 bar at peak, and uses radar for collision avoidance and standoff control. Reverse osmosis water can be specified where surface finish, seals or painted surfaces require it.",
    "Maximum take-off mass is 29 kg. The sub 25 kg limit that applied under the earlier authorisation route is not required under UK SORA.",
    "Working height Over 60 metres",
    "Flow rate Up to 15 litres per minute",
    "Working pressure Around 170 bar at the nozzle, up to 255 bar at peak",
    "Collision avoidance Radar, with standoff control",
    "Maximum take-off mass 29 kg",
    "The drone, pressure system and nozzle set specified against your surfaces.",
    "Pilot training is available as an additional service, and we can advise on preparing the operations manual and supporting documentation required for CAA authorisation.",
    "Parts are held in the United Kingdom, repairs are carried out in our own workshop, and the enhanced warranty option provides priority servicing and maintenance, with loan equipment where parts are unavailable. We also offer white label services, arranged in advance, giving clients additional capacity.",
    "Cleaning operations at height adjacent to structures fall within the Specific Category, which requires an Operational Authorisation from the Civil Aviation Authority. Since April 2025 these are granted through UK SORA.",
    "The Operational Authorisation is held by the operator and not the supplier. The Bionic Eye assists clients in attaining their own, drawing on the UK SORA authorisation we hold for cleaning operations with our own PowerWash system, obtained in January 2026, and on the applications we have supported since. The first client Operational Authorisation for the C10 has now been granted, in the client's own name, with two further applications at final assessment.",
    "ABZ Innovation's case studies show what the C10 delivers in service. A factory facade was cleaned at around 300 square metres an hour using chemical-free reverse osmosis water. A roof carrying ten years of moss, about 550 square metres, was cleared in roughly three hours with no chemicals, and the system was set up and ready to fly in fifteen minutes.",
    "Figures are from ABZ Innovation case studies. Actual output varies with the surface, the level of soiling and site conditions.",
    "Send us the sites you intend to work on. We will identify which are straightforward under a standard authorisation, which require additional work, and which are unlikely to be viable, before any commitment is made.",
    "The Bionic Eye, Bionic House, Hall Farm, Berry Lane, Chorleywood, WD3 5EX, United Kingdom.",
    "Specialist brands: FarmingByDrone | PowerWash | CleaningByDrone",
    "CAA approved since 2014. UK SORA authorisation held for cleaning operations with the PowerWash system since January 2026.",
    "The Bionic Eye Ltd. Registered in England and Wales, company number 09053005. Registered office: 22 Wycombe End, Beaconsfield HP9 1NB.",
    "Discuss a requirement",
    "How authorisation works",
    "Name Company Email Telephone Sites or work involved",
]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            pass


def wait_for_url(url):
    for _ in range(100):
        try:
            response = requests.get(url, timeout=1)
            if response.ok:
                return response
        except requests.RequestException:
            pass
        time.sleep(.1)
    raise RuntimeError(f"Server did not start: {url}")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def check_media_files():
    required = [
        "assets/css/site.css", "assets/js/site.js", "index.php", "contact.php",
        "assets/videos/web/hero-desktop.mp4", "assets/videos/web/hero-mobile.mp4",
        "assets/videos/posters/c10-short.jpg", "assets/videos/posters/portrait-cleaning.jpg",
        "assets/images/optimized/c10-facade-cleaning-wide-640.webp",
        "assets/images/optimized/c10-facade-cleaning-wide-1280.webp",
        "assets/images/optimized/c10-facade-cleaning-close-up-640.webp",
    ]
    for rel in required:
        assert (ROOT / rel).is_file(), f"Missing required resource: {rel}"
    original_images = ["865AD018.jpg", "C10 3.jpg", "C10-2.png", "C10-5.png", "C10-7.png", "C10.png", "IMG_2224.jpg"]
    for name in original_images:
        assert (ROOT / "assets/images" / name).is_file(), f"Missing supplied photograph: {name}"
    assert (ROOT / "assets/images/bionic-eye-logo-black.png").is_file()
    assert (ROOT / "assets/images/bionic-eye-logo-white.png").is_file()
    for name in EXPECTED_SOURCE_VIDEOS:
        source = ROOT / "assets/videos" / name
        assert source.is_file(), f"Missing original client video: {name}"
        metadata = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,channels", "-of", "json", str(source)
        ], text=True))
        audio = [stream for stream in metadata["streams"] if stream.get("codec_type") == "audio"]
        assert audio and audio[0].get("codec_name") == "aac" and audio[0].get("channels") == 2, f"Original AAC stereo sound missing: {name}"


def check_c10_page(browser, url):
    desktop = browser.new_page(viewport={"width": 1440, "height": 1000})
    desktop.goto(url, wait_until="domcontentloaded")
    desktop.evaluate("""() => {
      document.querySelectorAll('img').forEach(img => img.loading = 'eager');
      document.querySelectorAll('[data-reveal]').forEach(el => el.classList.add('is-visible'));
    }""")
    desktop.wait_for_function("() => [...document.images].every(i => i.complete && i.naturalWidth > 0)", timeout=30000)
    desktop.wait_for_function("() => document.querySelector('.hero__video')?.currentSrc.includes('hero-desktop.mp4')", timeout=15000)
    assert desktop.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Desktop horizontal overflow"
    order = desktop.locator("main > section").evaluate_all("els => els.map(e => e.id || [...e.classList].find(c => c.endsWith('-section'))) ")
    assert order == ["home", "applications", "system", "supply", "regulation", "field-section", "enquiry"], order
    desktop.keyboard.press("Tab")
    assert desktop.locator(".skip-link").is_visible(), "Skip-to-content is not keyboard-visible"
    assert desktop.evaluate("document.activeElement.getAttribute('href')") == "#main-content"
    assert desktop.locator("#primary-navigation a").all_text_contents() == EXPECTED_NAV
    assert desktop.locator("#home.hero").count() == 1
    assert desktop.locator(".application-list li").all_text_contents() == EXPECTED_APPLICATIONS

    app_paths = desktop.locator(".application-visual img").evaluate_all("imgs => imgs.map(i => i.getAttribute('src'))")
    assert [unquote(x) for x in app_paths] == ["assets/images/C10 3.jpg", "assets/images/865AD018.jpg", "assets/images/IMG_2224.jpg"], app_paths
    product_paths = desktop.locator(".product-image img").evaluate_all("imgs => imgs.map(i => i.getAttribute('src'))")
    assert product_paths == ["assets/images/C10-2.png", "assets/images/C10-5.png", "assets/images/C10-7.png", "assets/images/C10.png"], product_paths
    assert desktop.locator(".spec-grid").evaluate("el => el.tagName") == "DL"
    assert desktop.locator(".spec-grid dt").count() == desktop.locator(".spec-grid dd").count() == 5
    assert desktop.locator(".field-case").count() == 2
    assert desktop.locator(".field-results + .field-caveat").count() == 1, "Approved case-study caveat is not adjacent"
    text = " ".join(desktop.locator("body").inner_text().split())
    for copy in EXPECTED_COPY:
        assert " ".join(copy.split()) in text, f"Approved copy missing or changed: {copy[:85]}"
    assert desktop.locator("h1").count() == 1
    assert desktop.locator(".hero .action").get_attribute("href") == "#enquiry"
    assert desktop.locator("#regulation .action").get_attribute("href").startswith("mailto:info@thebioniceye.co.uk?subject=How%20authorisation%20works")
    sources = desktop.locator(".field-video source, .video-gallery source").evaluate_all("els => els.map(e => e.getAttribute('src'))")
    source_names = {unquote(path).split("/")[-1] for path in sources}
    assert len(sources) == 6 and source_names == EXPECTED_SOURCE_VIDEOS, source_names
    players = desktop.locator(".field-video, .video-gallery video").evaluate_all("els => els.map(v => ({controls:v.controls, muted:v.muted, preload:v.preload}))")
    assert len(players) == 6 and all(v["controls"] and not v["muted"] and v["preload"] == "none" for v in players)

    image_info = desktop.evaluate("""() => [...document.images].map(i => ({alt:i.alt,loaded:i.complete && i.naturalWidth>0}))""")
    assert len(image_info) >= 9 and all(item["alt"].strip() and item["loaded"] for item in image_info), image_info
    source_sets = desktop.locator("picture source[type='image/webp']").count()
    assert source_sets >= 7, f"Responsive WebP sources missing: {source_sets}"
    assert not desktop.evaluate("""() => [...document.querySelectorAll('a[href^="#"]')].some(a => !document.getElementById(a.getAttribute('href').slice(1)))""")

    mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    mobile.goto(url, wait_until="domcontentloaded")
    mobile.evaluate("document.querySelectorAll('img').forEach(i => i.loading = 'eager')")
    mobile.wait_for_function("() => [...document.images].every(i => i.complete && i.naturalWidth > 0)", timeout=30000)
    mobile.wait_for_function("() => document.querySelector('.hero__video')?.currentSrc.includes('hero-mobile.mp4')", timeout=15000)
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Mobile horizontal overflow"
    menu = mobile.locator(".menu-toggle")
    menu.click()
    assert menu.get_attribute("aria-expanded") == "true" and mobile.locator("#primary-navigation").is_visible()
    assert mobile.locator("#primary-navigation a", has_text="Home").count() == 1
    mobile.locator("#primary-navigation a", has_text="Regulation").click()
    assert mobile.url.endswith("#regulation") and menu.get_attribute("aria-expanded") == "false"
    sound = mobile.locator(".audio-toggle")
    sound.click()
    mobile.wait_for_function("!document.querySelector('.hero__video').muted", timeout=5000)
    assert sound.get_attribute("aria-label") == "Mute hero video sound"
    sound.click()
    mobile.wait_for_function("document.querySelector('.hero__video').muted", timeout=5000)

    form = mobile.locator(".enquiry-form")
    mobile.locator("#name").fill("QA Person")
    mobile.locator("#email").fill("invalid-address")
    mobile.locator("#sites").fill("QA-only, not submitted")
    assert not form.evaluate("f => f.checkValidity()")
    mobile.locator("#email").fill("qa@example.org")
    form.dispatch_event("submit")
    assert "static preview" in mobile.locator(".form-status").inner_text().lower()

    reduced = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    reduced.goto(url, wait_until="domcontentloaded")
    assert reduced.locator(".hero__video").is_hidden()
    assert reduced.locator(".hero__controls").is_hidden()
    print("PASS C10 visual QA: 1440/390 widths, Home/menu, exact copy and order, seven photos, five-row specs, six audible source videos, webp, form accessibility and reduced motion")
    desktop.close(); mobile.close(); reduced.close()


def check_php_form():
    port = free_port()
    process = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", str(ROOT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/"
    try:
        client = requests.Session()
        wait_for_url(base)
        page = client.get(base, timeout=10)
        token_match = re.search(r'name="csrf_token" value="([a-f0-9]{64})"', page.text)
        started_match = re.search(r'name="form_started_at" value="(\d+)"', page.text)
        assert token_match and started_match, "PHP index did not inject session token and form timestamp"
        # The bot-trap path deliberately acknowledges without sending or storing a message.
        payload = {
            "csrf_token": token_match.group(1), "form_started_at": str(int(started_match.group(1)) - 10),
            "project": "asset-cleaning", "website": "automated-test", "name": "QA Person",
            "company": "", "email": "qa@example.org", "telephone": "", "sites": "Never sent to the company",
        }
        response = client.post(base + "contact.php", data=payload, headers={"Accept": "application/json"}, timeout=10)
        assert response.status_code == 200 and response.json().get("ok") is True, response.text
        invalid = dict(payload, website="", email="not-an-email")
        response = client.post(base + "contact.php", data=invalid, headers={"Accept": "application/json"}, timeout=10)
        assert response.status_code == 422, response.text
        invalid_token = dict(payload, csrf_token="0" * 64)
        response = client.post(base + "contact.php", data=invalid_token, headers={"Accept": "application/json"}, timeout=10)
        assert response.status_code == 403, response.text
        print("PASS PHP form QA: dynamic token, safe honeypot acknowledgement, invalid email and forged-token rejection; no real email sent")
    finally:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill()


def main():
    check_media_files()
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"])
            check_c10_page(browser, f"http://127.0.0.1:{server.server_port}/")
            browser.close()
        check_php_form()
    finally:
        server.shutdown(); server.server_close()


if __name__ == "__main__":
    main()
