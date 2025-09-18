# ---------------- nvbus_railway.py ----------------
import os
import time
import threading
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template_string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twilio.rest import Client
from selenium.webdriver.chrome.service import Service


# ---------------- Logging Setup ----------------
logging.basicConfig(level=logging.WARNING)  # Reduce Railway spam
logger = logging.getLogger(__name__)

# ---------------- Twilio Setup ----------------
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = os.getenv("FROM_WHATSAPP")
TO_WHATSAPP = os.getenv("TO_WHATSAPP")

# ---------------- Status Tracker ----------------
status_info = {
    "last_run": None,
    "status": "Never run",
    "message_preview": None
}

def send_whatsapp_message(message):
    """Send WhatsApp message via Twilio"""
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP
        )
        logger.warning("WhatsApp message sent!")
        status_info["message_preview"] = (message[:200] + "...") if len(message) > 200 else message
    except Exception as e:
        logger.error("Failed to send WhatsApp message: %s", e)
        status_info["message_preview"] = f"Error sending: {e}"

# ---------------- NVBus Helper Functions ----------------
def get_total_price(driver):
    total_divs = driver.find_elements(By.CSS_SELECTOR, "div.fairdetails")
    for div in total_divs:
        try:
            p_text = div.find_element(By.TAG_NAME, "p").text.strip()
            if "Total Amount" in p_text:
                return div.find_element(By.TAG_NAME, "label").text.strip()
        except:
            continue
    return None

def select_seat_and_get_price(driver, seat_number):
    seat = driver.find_element(By.XPATH, f"//span[text()='{seat_number}']/parent::div")
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", seat)
    time.sleep(1)
    seat.click()
    time.sleep(2)
    return get_total_price(driver)

# ---------------- Main NVBus Scraper ----------------
def scrape_nvbus_prices():
    """Main scraper job for NVBus"""
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.binary_location = "/usr/bin/chromium"

        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)



        today = datetime.today()
        today_date = datetime(today.year, today.month, today.day)
        good_luck_date = datetime(2025, 10, 6)

        if today_date == good_luck_date:
            send_whatsapp_message("Good Luck! 🍀")
            status_info.update({"last_run": datetime.now(), "status": "Success"})
            return

        dates_to_scrape = [
            (21, 9, 2025),
            (28, 9, 2025),
            (5, 10, 2025)
        ]

        message = "Ryan's little Project :\n"

        driver.get("https://nvbus.in/")
        time.sleep(3)

        try:
            driver.find_element(By.CSS_SELECTOR, "button.btn-close").click()
        except:
            pass
        time.sleep(1)

        from_city = driver.find_element(By.ID, "FromCity")
        from_city.send_keys("Bangalore")
        from_city.send_keys(Keys.RETURN)

        to_city = driver.find_element(By.ID, "ToCity")
        to_city.send_keys("Durg")
        to_city.send_keys(Keys.RETURN)

        for day, month, year in dates_to_scrape:
            date_obj = datetime(year, month, day)
            if date_obj < today_date:
                continue

            date_input = driver.find_element(By.ID, "txtFromDate")
            driver.execute_script("arguments[0].value = '';", date_input)
            driver.execute_script("arguments[0].click();", date_input)
            time.sleep(1)

            target_month_year = date_obj.strftime("%B %Y")
            while True:
                header = driver.find_element(By.CSS_SELECTOR, ".datepicker-days .datepicker-switch").text
                if target_month_year in header:
                    break
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".datepicker-days th.next"))
                )
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(0.5)

            driver.find_element(By.XPATH, f"//div[@class='datepicker-days']//td[normalize-space()='{day}']").click()
            time.sleep(1)

            driver.find_element(By.CSS_SELECTOR, "button.searchbtn").click()
            time.sleep(5)

            first_bus_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "SelectseatTab_0"))
            )
            driver.execute_script("arguments[0].click();", first_bus_button)
            time.sleep(3)

            single_price = select_seat_and_get_price(driver, "L8")
            driver.find_element(By.XPATH, "//span[text()='L8']/parent::div").click()
            time.sleep(1)
            double_price = select_seat_and_get_price(driver, "L9")

            message += (
                f"\nDate: {day:02d}-{month:02d}-{year}\n"
                f"Single Seat (L8) Total Price: {single_price}\n"
                f"Double Seat (L9) Total Price: {double_price}\n"
            )

            driver.get("https://nvbus.in/")
            time.sleep(3)
            try:
                driver.find_element(By.CSS_SELECTOR, "button.btn-close").click()
            except:
                pass

            from_city = driver.find_element(By.ID, "FromCity")
            from_city.send_keys("Bangalore")
            from_city.send_keys(Keys.RETURN)
            to_city = driver.find_element(By.ID, "ToCity")
            to_city.send_keys("Durg")
            to_city.send_keys(Keys.RETURN)

        send_whatsapp_message(message.strip())
        status_info.update({"last_run": datetime.now(), "status": "Success"})

    except Exception as e:
        logger.error("Scraping failed: %s", e)
        status_info.update({"last_run": datetime.now(), "status": f"Failed - {e}"})
    finally:
        if driver:
            driver.quit()

# ---------------- Flask + Scheduler ----------------
app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.add_job(scrape_nvbus_prices, 'cron', hour=15, minute=0)   # 20:30 IST
scheduler.add_job(scrape_nvbus_prices, 'cron', hour=4, minute=30)   # 10:00 IST
scheduler.start()

@app.route("/")
def home():
    return render_template_string("""
    <html>
    <head>
        <title>Ryan's little Project</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
            h1 { color: #333; }
            button {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 15px 30px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 18px;
                border-radius: 8px;
                cursor: pointer;
                transition: background 0.3s ease;
            }
            button:hover { background-color: #45a049; }
            a { display:block; margin-top:20px; color:#007BFF; text-decoration:none; }
        </style>
    </head>
    <body>
        <h1>Ryan's little project </h1>
        <p>Click below to run the scraper on demand:</p>
        <form action="/scrape" method="post">
            <button type="submit">Run Scraper 🚀</button>
        </form>
        <a href="/status">📊 View Status</a>
    </body>
    </html>
    """)

@app.route("/scrape", methods=["POST"])
def run_scraper():
    threading.Thread(target=scrape_nvbus_prices).start()
    return "Scraper triggered! 🚀 Check WhatsApp for updates."

@app.route("/status")
def status_page():
    last_run = status_info["last_run"].strftime("%Y-%m-%d %H:%M:%S") if status_info["last_run"] else "Never"
    return render_template_string(f"""
    <html>
    <head>
        <title>Status - Ryan's little Project</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
            h1 {{ color: #333; }}
            .card {{ background: #f8f8f8; padding: 20px; border-radius: 10px; display: inline-block; }}
        </style>
    </head>
    <body>
        <h1>📊 Check Status</h1>
        <div class="card">
            <p><b>Last Run:</b> {last_run}</p>
            <p><b>Status:</b> {status_info["status"]}</p>
            <p><b>Last Message Preview:</b><br>{status_info["message_preview"] or "None"}</p>
        </div>
        <br><br>
        <a href="/">⬅ Back to Home</a>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
