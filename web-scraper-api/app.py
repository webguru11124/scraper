from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

app = Flask(__name__)

logger = logging.getLogger(__name__)


@app.route("/scrape", methods=["GET"])
def scrape():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()), options=options
        )
    except Exception as e:
        logger.error(f"Error installing ChromeDriver: {e}")
        return jsonify({"error": str(e)}, status=500)

    try:
        driver.get("https://members.collegeofopticians.ca/Public-Register")
        logger.info("Navigated to the public register page.")

        # Click the "Find" button
        try:
            find_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//input[@value="Find"]'))
            )
            find_button.click()
            logger.info("Clicked the 'Find' button.")
        except Exception as e:
            logger.error(f"Error clicking 'Find' button: {e}")
            driver.quit()
            return jsonify({"error": f"Error clicking 'Find' button: {e}"}, status=500)

        # Wait for the table to appear
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody"))
            )
            logger.info("Table appeared.")
        except Exception as e:
            logger.error(f"Error waiting for table: {e}")
            driver.quit()
            return jsonify({"error": f"Error waiting for table: {e}"}, status=500)

        # Extract data from the first page
        data = extract_table_data(driver)

        # Check for pagination and navigate if necessary
        while True:
            try:
                next_button = driver.find_element(By.LINK_TEXT, "Next")
                if "disabled" in next_button.get_attribute("class"):
                    logger.info("No more pages to navigate.")
                    break
                else:
                    next_button.click()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody"))
                    )
                    data.extend(extract_table_data(driver))
                    logger.info("Navigated to next page.")
            except Exception as e:
                logger.info(f"No more pages to navigate or error occurred: {e}")
                break

        driver.quit()
        return jsonify({"data": data})
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        driver.quit()
        return jsonify({"error": str(e)}, status=500)


def extract_table_data(driver):
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    page_data = []
    for row in rows:
        columns = row.find_elements(By.TAG_NAME, "td")
        registrant = columns[0].text.strip()
        status = columns[1].text.strip()
        reg_class = columns[2].text.strip()
        location = columns[3].text.strip()
        details_link = (
            columns[4].find_element(By.TAG_NAME, "a").get_attribute("href").strip()
        )
        page_data.append(
            {
                "registrant": registrant,
                "status": status,
                "class": reg_class,
                "location": location,
                "details_link": details_link,
            }
        )
    return page_data


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
