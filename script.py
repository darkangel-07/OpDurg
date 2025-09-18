import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twilio.rest import Client
import chromedriver_autoinstaller

# ---------------- Twilio Setup (from env vars) ----------------
TWILIO_SID = os.environ["TWILIO_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
FROM_WHATSAPP = os.environ["FROM_WHATSAPP"]
TO_WHATSAPP = os.environ["TO_WHATSAPP"]

def send_whatsapp_message(message):
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(
        body=message,
        from_=FROM_WHATSAPP,
        to=TO_WHATSAPP
    )
    print("WhatsApp message sent!")

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

# ---------------- Main NVBus Script ----------------
def scrape_and_send_prices():
    # Install correct ChromeDriver automatically
    chromedriver_autoinstaller.install()

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # headless mode for Railway
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    today = datetime.today()
    today_date = datetime(today.year, today.month, today.day)
    good_luck_date = datetime(2025, 10, 6)

    if today_date == good_luck_date:
        send_whatsapp_message("Good Luck! 🍀")
        print("Good Luck message sent for 06-10-2025")
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

        # Close popup
        try:
            driver.find_element(By.CSS_SELECTOR, "button.btn-close").click()
            print("Popup closed.")
        except:
            print("No popup found.")
        time.sleep(1)

        # From City = Bangalore
        from_city = driver.find_element(By.ID, "FromCity")
        from_city.send_keys("Bangalore")
        time.sleep(1)
        from_city.send_keys(Keys.RETURN)

        # To City = Durg
        to_city = driver.find_element(By.ID, "ToCity")
        to_city.send_keys("Durg")
        time.sleep(1)
        to_city.send_keys(Keys.RETURN)

        for day, month, year in dates_to_scrape:
            date_obj = datetime(year, month, day)
            if date_obj < today_date:
                print(f"Skipping {day:02d}-{month:02d}-{year} (past date)")
                continue

            # Clear previous date
            date_input = driver.find_element(By.ID, "txtFromDate")
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", date_input)
            time.sleep(1)
            driver.execute_script("arguments[0].value = '';", date_input)
            driver.execute_script("arguments[0].click();", date_input)
            time.sleep(1)

            # Navigate calendar to correct month
            target_month_year = date_obj.strftime("%B %Y")
            while True:
                header = driver.find_element(By.CSS_SELECTOR, ".datepicker-days .datepicker-switch").text
                if target_month_year in header:
                    break
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".datepicker-days th.next"))
                )
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                time.sleep(0.5)
                next_button.click()
                time.sleep(0.5)

            # Select day
            driver.find_element(By.XPATH, f"//div[@class='datepicker-days']//td[normalize-space()='{day}']").click()
            time.sleep(1)
            print(f"Date set to {day:02d}-{month:02d}-{year}")

            # Click Search
            driver.find_element(By.CSS_SELECTOR, "button.searchbtn").click()
            time.sleep(5)

            # Scroll + Click "View Seats"
            first_bus_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "SelectseatTab_0"))
            )
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", first_bus_button)
            time.sleep(1)
            first_bus_button.click()
            time.sleep(3)

            # Single Seat L8
            single_price = select_seat_and_get_price(driver, "L8", "Single Seat")
            # Unselect L8
            seat_L8 = driver.find_element(By.XPATH, "//span[text()='L8']/parent::div")
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", seat_L8)
            time.sleep(1)
            seat_L8.click()
            time.sleep(2)

            # Double Seat L9
            double_price = select_seat_and_get_price(driver, "L9", "Double Seat")

            # Add results to message
            message += (
                f"\nDate: {day:02d}-{month:02d}-{year}\n"
                f"Single Seat (L8) Total Price: {single_price}\n"
                f"Double Seat (L9) Total Price: {double_price}\n"
            )

            # Close and start fresh for next date
            driver.get("https://nvbus.in/")
            time.sleep(3)
            try:
                driver.find_element(By.CSS_SELECTOR, "button.btn-close").click()
            except:
                pass
            time.sleep(1)

            # Re-enter cities
            from_city = driver.find_element(By.ID, "FromCity")
            from_city.send_keys("Bangalore")
            time.sleep(1)
            from_city.send_keys(Keys.RETURN)

            to_city = driver.find_element(By.ID, "ToCity")
            to_city.send_keys("Durg")
            time.sleep(1)
            to_city.send_keys(Keys.RETURN)

        # Send WhatsApp message
        send_whatsapp_message(message.strip())
        print("Bus prices sent!")

    finally:
        driver.quit()

# ---------------- Optional Flask Trigger ----------------
from flask import Flask
app = Flask(__name__)

@app.route("/run")
def run_script():
    scrape_and_send_prices()
    return "Script executed!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
