import json
import os
import requests
import boto3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

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
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
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
                cursor.execute("INSERT INTO scraped_data (data) VALUES (%s)", (json.dumps(data),))
                connection.commit()
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Data inserted successfully', 'data': data})
    }
