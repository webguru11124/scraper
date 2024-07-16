#!/bin/bash

set -e

# Retrieve the instance ID of the EC2 instance
INSTANCE_ID=$(aws ec2 describe-instances \
    --query 'Reservations[*].Instances[*].InstanceId' \
    --filters 'Name=tag:Name,Values=CdkInfraStack/EC2Instance' \
    --output text \
    --profile alex)

if [ -z "$INSTANCE_ID" ]; then
    echo "EC2 instance ID not found"
    exit 1
fi

# Copy the Django project to the EC2 instance using SSM
aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters commands=["mkdir -p /home/ec2-user/web-scraper-api/scraper_project", "aws s3 cp s3://my-bucket/scraper_project.zip /home/ec2-user/web-scraper-api/scraper_project.zip", "unzip -o /home/ec2-user/web-scraper-api/scraper_project.zip -d /home/ec2-user/web-scraper-api/scraper_project"] \
    --output text \
    --profile alex

# Run setup commands on the EC2 instance using SSM
aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters commands=["cd /home/ec2-user/web-scraper-api/scraper_project", "python3 manage.py migrate", "sudo systemctl restart django"] \
    --output text \
    --profile alex
