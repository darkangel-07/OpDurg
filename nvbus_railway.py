# ---------------- nvbus_railway.py ----------------
import time
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twilio.rest import Client
import chromedriver_autoinstaller

# ---------------- Twilio Setup ----------------
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = os.environ.get("FROM_WHATSAPP")
TO_WHATSAPP = os.environ.get("TO_WHATSAPP")


client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

def send_whatsapp_message(message):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP
        )
        print("WhatsApp message sent!")
    except Exception as e:
        print("Failed to send WhatsApp message:", e)

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

def select_seat_and_get_price(driver, seat_number, label):
    seat = driver.find_element(By.XPATH, f"//span[text()='{seat_number}']/parent::div")
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", seat)
    time.sleep(1)
    seat.click()
    time.sleep(2)
    fare = get_total_price(driver)
    print(f"{label} ({seat_number}) Total Price = {fare}")
    return fare

# ---------------- Main NVBus Scraper ----------------
def scrape_nvbus_prices():
    chromedriver_autoinstaller.install()
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)

    today = datetime.today()
    today_date = datetime(today.year, today.month, today.day)
    good_luck_date = datetime(2025, 10, 6)

    if today_date == good_luck_date:
        send_whatsapp_message("Good Luck! 🍀")
        driver.quit()
        return

    dates_to_scrape = [
        (21, 9, 2025),
        (28, 9, 2025),
        (5, 10, 2025)
    ]

    message = "NVBus Prices:\n"

    try:
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

            single_price = select_seat_and_get_price(driver, "L8", "Single Seat")
            driver.find_element(By.XPATH, "//span[text()='L8']/parent::div").click()
            time.sleep(2)
            double_price = select_seat_and_get_price(driver, "L9", "Double Seat")

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

    finally:
        driver.quit()

# ---------------- Flask + Scheduler ----------------
app = Flask(__name__)
scheduler = BackgroundScheduler()

# Schedule scraper every day at 07:00 UTC (adjust if needed)
scheduler.add_job(scrape_nvbus_prices, 'cron', hour=15, minute=0)
scheduler.add_job(scrape_nvbus_prices, 'cron', hour=4, minute=30)
scheduler.start()

@app.route("/")
def home():
    return "NVBus Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
