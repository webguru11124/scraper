import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import psycopg2

def handler(event, context):
    db_endpoint = os.getenv("DB_ENDPOINT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    connection = psycopg2.connect(
        host=db_endpoint,
        database=db_name,
        user=db_user,
        password=db_password
    )

    cursor = connection.cursor()

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    driver.get('https://members.collegeofopticians.ca/Public-Register')

    # Implement your scraping logic here
    data = driver.find_element_by_tag_name('body').text  # Example

    cursor.execute("INSERT INTO scraped_data (data) VALUES (%s)", (data,))
    connection.commit()

    cursor.close()
    connection.close()
    driver.quit()

    return {
        'statusCode': 200,
        'body': json.dumps({'data': data})
    }
