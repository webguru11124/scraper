import json
import os
import requests
import boto3
import logging

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

def execute_sql(sql, sql_parameters):
    client = boto3.client('rds-data')
    response = client.execute_statement(
        resourceArn=os.getenv('DB_CLUSTER_ARN'),
        secretArn=os.getenv('DB_SECRET_ARN'),
        database=os.getenv('DB_NAME'),
        sql=sql,
        parameters=sql_parameters
    )
    return response

def lambda_handler(event, context):
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
        # Clear the existing data
        truncate_sql = "TRUNCATE TABLE scraped_data"
        execute_sql(truncate_sql, [])
        logger.info("Cleared the scraped_data table.")
        
        # Insert new data
        insert_sql = """
        INSERT INTO scraped_data (registrant, status, class, location, details_link)
        VALUES (:registrant, :status, :class, :location, :details_link)
        """
        for record in data:
            sql_parameters = [
                {'name': 'registrant', 'value': {'stringValue': record['registrant']}},
                {'name': 'status', 'value': {'stringValue': record['status']}},
                {'name': 'class', 'value': {'stringValue': record['class']}},
                {'name': 'location', 'value': {'stringValue': record['location']}},
                {'name': 'details_link', 'value': {'stringValue': record['details_link']}}
            ]
            execute_sql(insert_sql, sql_parameters)
        
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
