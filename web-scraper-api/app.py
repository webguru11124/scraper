from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
import logging

app = Flask(__name__)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('scraper.log')

# Create formatters and add them to handlers
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)
file_handler.setFormatter(file_format)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

@app.route("/scrape", methods=["GET"])
def scrape():
    last_name = request.args.get('last_name', '')
    first_name_contains = request.args.get('first_name_contains', '')
    informal_name_contains = request.args.get('informal_name_contains', '')
    registration_number = request.args.get('registration_number', '')
    registration_class = request.args.get('registration_class', '')
    registration_status = request.args.get('registration_status', '')
    contact_lens_mentor = request.args.get('contact_lens_mentor', '')
    area_of_service = request.args.get('area_of_service', '')
    language_of_service = request.args.get('language_of_service', '')
    practice_name = request.args.get('practice_name', '')
    city_or_town = request.args.get('city_or_town', '')
    postal_code = request.args.get('postal_code', '')

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-software-rasterizer")

    try:
        # driver_path = ChromeDriverManager().install()
        # logger.info(f"ChromeDriver path: {driver_path}")
        # service = Service('/usr/local/bin/chromedriver')
        # driver = webdriver.Chrome(service=service, options=options)
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        logger.error(f"Error installing ChromeDriver: {e}")
        return jsonify({"error": str(e)}), 500

    try:
        driver.get("https://members.collegeofopticians.ca/Public-Register")
        logger.info("Navigated to the public register page.")

        # Fill out the form fields
        try:
            driver.find_element(By.ID, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input0_TextBox1').send_keys(last_name)
            driver.find_element(By.ID, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input1_TextBox1').send_keys(first_name_contains)
            driver.find_element(By.ID, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input2_TextBox1').send_keys(informal_name_contains)
            driver.find_element(By.ID, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input3_TextBox1').send_keys(registration_number)

            # TODO: check if value is in correct options format.

            set_dropdown_value(driver, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input4_DropDown1',registration_class)
            set_dropdown_value(driver, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input5_DropDown1',registration_status)
            set_dropdown_value(driver, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input6_DropDown1',contact_lens_mentor)
            set_dropdown_value(driver, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input7_DropDown1',area_of_service)

            # TODO: check if this is working for searchable dropdown since it is not in the select2 format.
            # set_dropdown_value(driver, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input5_DropDown1',registration_status)select2-tags-container')).select_by_visible_text(language_of_service)

            driver.find_element(By.ID, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input9_TextBox1').send_keys(practice_name)
            driver.find_element(By.ID, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input10_TextBox1').send_keys(city_or_town)
            driver.find_element(By.ID, 'ctl01_TemplateBody_WebPartManager1_gwpciNewQueryMenuCommon_ciNewQueryMenuCommon_ResultsGrid_Sheet0_Input11_TextBox1').send_keys(postal_code)
            logger.info("Filled out the form fields.")
        except Exception as e:
            logger.error(f"Error filling out form fields: {e}")
            driver.quit()
            return jsonify({"error": f"Error filling out form fields: {e}"}), 500

        # Click the "Find" button
        try:
            find_button = WebDriverWait(driver, 100).until(
                EC.element_to_be_clickable((By.XPATH, '//input[@value="Find"]'))
            )
            find_button.click()
            logger.info("Clicked the 'Find' button.")
        except Exception as e:
            logger.error(f"Error clicking 'Find' button: {e}")
            driver.quit()
            return jsonify({"error": f"Error clicking 'Find' button: {e}"}), 500

        # Wait for the table to appear
        try:
            WebDriverWait(driver, 2000).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody"))
            )
            logger.info("Table appeared.")
        except Exception as e:
            logger.error(f"Error waiting for table: {e}")
            driver.quit()
            return jsonify({"error": f"Error waiting for table: {e}"}), 500

        # Extract data from the first page
        data = extract_table_data(driver)

         # Check for pagination and navigate if necessary
        while True:
            try: 
                next_button = WebDriverWait(driver, 100).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[title='Next Page']"))
                )
                if not next_button.is_enabled() or next_button.get_attribute("onclick") == "return false;":
                    logger.info("No more pages to navigate.")
                    break
                else:
                    next_button.click()
                    WebDriverWait(driver, 2000).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody"))
                    )
                    data.extend(extract_table_data(driver))
                    logger.info("Navigated to next page.")
            except StaleElementReferenceException:
                logger.info("Stale element reference exception occurred, retrying.")
                continue
            except Exception as e:
                logger.info(f"No more pages to navigate or error occurred: {e}")
                break

        driver.quit()
        logger.info(f"Scraping completed. Found {len(data)} records.")
        return jsonify({"data": data})
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        driver.quit()
        return jsonify({"error": str(e)}), 500

def set_dropdown_value(driver, dropdown_id, value):
    try:
        select_element = Select(driver.find_element(By.ID, dropdown_id))
        options = [option.text for option in select_element.options]
        logger.info(f"Available options for {dropdown_id}: {options}")
        if value in options:
            select_element.select_by_visible_text(value)
        else:
            logger.warning(f"Value '{value}' not found in options for {dropdown_id}")
    except NoSuchElementException as e:
        logger.error(f"Dropdown with id {dropdown_id} not found: {e}")
        raise e
    
def extract_table_data(driver):
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    page_data = []
    for row in rows:
        columns = row.find_elements(By.CSS_SELECTOR, "td[role='gridcell']")
        if len(columns) == 0:
            continue  # Skip rows without valid columns
        registrant = columns[0].text.strip()
        status = columns[1].text.strip()
        reg_class = columns[2].text.strip()
        location = columns[3].text.strip()
        details_link = (
            columns[4].find_element(By.TAG_NAME, "a").get_attribute("href").strip()
            if len(columns) > 4 and columns[4].find_elements(By.TAG_NAME, "a")
            else ""
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
