#!/bin/bash

set -e

# Fetch the EC2 instance public DNS from CloudFormation stack output
INSTANCE_DNS=$(aws cloudformation describe-stacks \
    --stack-name CdkInfraStack \
    --query 'Stacks[0].Outputs[?OutputKey==`EC2InstancePublicDNS`].OutputValue' \
    --output text \
    --profile alex)

if [ -z "$INSTANCE_DNS" ]; then
    echo "EC2 instance DNS not found"
    exit 1
fi

# Copy the Django project to the EC2 instance
scp -i ~/.ssh/ec2-key-pair.pem -r ./scraper_project ec2-user@$INSTANCE_DNS:/home/ec2-user/web-scraper-api

# Run setup commands on the EC2 instance
ssh -i ~/.ssh/ec2-key-pair.pem ec2-user@$INSTANCE_DNS << EOF
sudo mkdir -p /home/ec2-user/web-scraper-api/scraper_project
sudo chown -R ec2-user:ec2-user /home/ec2-user/web-scraper-api
cd /home/ec2-user/web-scraper-api/scraper_project
python3 manage.py migrate
sudo systemctl restart django || sudo systemctl start django
EOF