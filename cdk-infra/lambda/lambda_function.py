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
    resource_arn = os.getenv('DB_CLUSTER_ARN')
    secret_arn = os.getenv('DB_SECRET_ARN')
    database = os.getenv('DB_NAME')
    
    if not resource_arn or not secret_arn or not database:
        logger.error("One or more required environment variables are missing.")
        logger.error(f"DB_CLUSTER_ARN: {resource_arn}")
        logger.error(f"DB_SECRET_ARN: {secret_arn}")
        logger.error(f"DB_NAME: {database}")
        raise ValueError("Required environment variables are not set.")

    client = boto3.client('rds-data')
    response = client.execute_statement(
        resourceArn=resource_arn,
        secretArn=secret_arn,
        database=database,
        sql=sql,
        parameters=sql_parameters
    )
    return response

def table_exists(table_name):
    check_table_sql = f"""
    SELECT COUNT(*)
    FROM information_schema.tables 
    WHERE table_name = '{table_name}'
    """
    response = execute_sql(check_table_sql, [])
    return response['records'][0][0]['longValue'] > 0

def create_table():
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS scraped_data (
        registrant VARCHAR(255),
        status VARCHAR(255),
        class VARCHAR(255),
        location VARCHAR(255),
        details_link VARCHAR(255)
    )
    """
    execute_sql(create_table_sql, [])
    logger.info("scraped_data table created successfully.")

def lambda_handler(event, context):
    instance_dns = os.getenv("EC2_INSTANCE_DNS")
    if not instance_dns:
        logger.error("EC2_INSTANCE_DNS environment variable is not set.")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'EC2_INSTANCE_DNS environment variable is not set.'})
        }

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
        # Check if the table exists, create it if it does not
        if not table_exists('scraped_data'):
            create_table()
        
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
