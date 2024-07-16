#!/bin/bash

set -e

# Define the project directory
PROJECT_DIR="./web-scraper-api"

# Check if the project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Project directory $PROJECT_DIR does not exist."
    exit 1
fi

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

# Copy the Flask project to the EC2 instance
scp -i ~/.ssh/ec2-key-pair.pem -r $PROJECT_DIR ec2-user@$INSTANCE_DNS:/home/ec2-user

# Run setup commands on the EC2 instance
ssh -i ~/.ssh/ec2-key-pair.pem ec2-user@$INSTANCE_DNS << 'EOF'
set -e

# Navigate to the project directory
cd /home/ec2-user/web-scraper-api

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the required packages
pip3 install -r requirements.txt

# Set Flask environment variables
export FLASK_APP=app.py
export FLASK_ENV=production

# Create systemd service file for Flask app
echo "[Unit]
Description=Gunicorn instance to serve Flask web scraper
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/web-scraper-api
Environment="PATH=/home/ec2-user/web-scraper-api/venv/bin"
ExecStart=/home/ec2-user/web-scraper-api/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:80 app:app

[Install]
WantedBy=multi-user.target
" | sudo tee /etc/systemd/system/web-scraper.service

# Reload systemd to apply the new service
sudo systemctl daemon-reload

# Start and enable the Flask app service
sudo systemctl start web-scraper.service
sudo systemctl enable web-scraper.service

EOF

echo "Deployment to EC2 instance completed successfully"