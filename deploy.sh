#!/bin/bash

set -e

# Define the project directory
PROJECT_DIR="./web-scraper-api"

# Check if the project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Project directory $PROJECT_DIR does not exist."
    exit 1
fi

# Fetch the EC2 instance public DNS from environment variable or CloudFormation stack output
if [ -z "$INSTANCE_DNS" ]; then
    echo "INSTANCE_DNS environment variable is not set. Fetching from CloudFormation stack output..."
    INSTANCE_DNS=$(aws cloudformation describe-stacks \
        --stack-name CdkInfraStack \
        --query 'Stacks[0].Outputs[?OutputKey==`EC2InstancePublicDNS`].OutputValue' \
        --output text)
fi

if [ -z "$INSTANCE_DNS" ]; then
    echo "EC2 instance DNS not found"
    exit 1
fi

# Copy the Flask project to the EC2 instance
scp -o StrictHostKeyChecking=no -i "$PEM_KEY_FILE" -r "$PROJECT_DIR" ec2-user@"$INSTANCE_DNS":/home/ec2-user

# Run setup commands on the EC2 instance
ssh -o StrictHostKeyChecking=no -i "$PEM_KEY_FILE" ec2-user@"$INSTANCE_DNS" << EOF
set -e

# Update and install required packages
sudo yum update -y
sudo amazon-linux-extras install -y nginx1
sudo yum install -y python3 git

# Navigate to the project directory
cd /home/ec2-user/web-scraper-api

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the required packages
pip3 install -r requirements.txt
pip3 install gunicorn

# Set Flask environment variables
export FLASK_APP=app.py
export FLASK_ENV=production

# Create systemd service file for Gunicorn
echo "[Unit]
Description=Gunicorn instance to serve Flask web scraper
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/web-scraper-api
Environment=\"PATH=/home/ec2-user/web-scraper-api/venv/bin\"
ExecStart=/home/ec2-user/web-scraper-api/venv/bin/gunicorn --workers 3 --bind unix:/home/ec2-user/web-scraper-api/web-scraper.sock -m 007 app:app

[Install]
WantedBy=multi-user.target
" | sudo tee /etc/systemd/system/web-scraper.service

# Reload systemd to apply the new service
sudo systemctl daemon-reload

# Start and enable the Gunicorn service
sudo systemctl start web-scraper.service
sudo systemctl enable web-scraper.service


# Configure Nginx
echo "server {
    listen 80;
    server_name \$INSTANCE_DNS;

    location / {
        proxy_pass http://unix:/home/ec2-user/web-scraper-api/web-scraper.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}" | sudo tee /etc/nginx/conf.d/web-scraper.conf

# Start and enable Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx

EOF

echo "Deployment to EC2 instance completed successfully"
