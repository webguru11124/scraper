import json
import os
import requests
import boto3
import psycopg2
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_db_credentials():
    secret_arn = os.getenv("DB_SECRET_ARN")
    region_name = boto3.session.Session().region_name
    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])
    return secret["username"], secret["password"]

def lambda_handler(event, context):
    db_endpoint = os.getenv("DB_ENDPOINT")
    db_name = os.getenv("DB_NAME")
    db_user, db_password = get_db_credentials()
    instance_dns = os.getenv("EC2_INSTANCE_DNS")
    
    url = f"http://{instance_dns}/scrape"
    
    params = {
        'last_name': event.get('last_name', ''),
        'first_name_contains': event.get('first_name_contains', ''),
        'informal_name_contains': event.get('informal_name_contains', ''),
        'registration_number': event.get('registration_number', ''),
        'registration_class': event.get('registration_class', ''),
        'registration_status': event.get('registration_status', ''),
        'area_of_service': event.get('area_of_service', ''),
        'language_of_service': event.get('language_of_service', ''),
        'practice_name': event.get('practice_name', ''),
        'city_or_town': event.get('city_or_town', ''),
        'postal_code': event.get('postal_code', '')
    }

    logger.info(f"Requesting data from {url} with parameters: {params}")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json().get('data', [])
        logger.info(f"Received {len(data)} records from the scrape API.")
        
    except requests.RequestException as e:
        logger.error(f"Error during API request: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

    try:
        with psycopg2.connect(
            host=db_endpoint,
            database=db_name,
            user=db_user,
            password=db_password
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE scraped_data")
                logger.info("Cleared the scraped_data table.")
                
                for record in data:
                    cursor.execute(
                        """
                        INSERT INTO scraped_data (registrant, status, class, location, details_link)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (record['registrant'], record['status'], record['class'], record['location'], record['details_link'])
                    )
                connection.commit()
                logger.info("Data inserted successfully into the database.")
                
    except Exception as e:
        logger.error(f"Error during database insertion: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Data inserted successfully', 'data': data})
    }
