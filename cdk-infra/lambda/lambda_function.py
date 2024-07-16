import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_credentials():
    secret_arn = os.getenv("DB_SECRET_ARN")
    region_name = os.getenv("AWS_REGION", "us-east-1")
    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])
    return secret["username"], secret["password"]

def handler(event, context):
    db_endpoint = os.getenv("DB_ENDPOINT")
    db_name = os.getenv("DB_NAME")
    db_user, db_password = get_db_credentials()

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
