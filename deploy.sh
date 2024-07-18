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
        --output text \
        --profile alex)
fi

if [ -z "$INSTANCE_DNS" ]; then
    echo "EC2 instance DNS not found"
    exit 1
fi

# Ensure PEM key file is set
if [ -z "$PEM_KEY_FILE" ]; then
    echo "PEM_KEY_FILE environment variable is not set."
    exit 1
fi

# Copy the Flask project to the EC2 instance
echo "Copying project directory to EC2 instance..."
scp -o StrictHostKeyChecking=no -i "$PEM_KEY_FILE" -r "$PROJECT_DIR" ec2-user@"$INSTANCE_DNS":/home/ec2-user
echo "Project directory copied."

# Run setup commands on the EC2 instance
echo "Executing setup commands on EC2 instance..."
ssh -o StrictHostKeyChecking=no -i "$PEM_KEY_FILE" ec2-user@"$INSTANCE_DNS" << EOF
set -e
echo "Updating packages..."
sudo yum update -y

echo "Installing nginx..."
sudo amazon-linux-extras install -y nginx1

echo "Installing Python3 and git..."
sudo yum install -y python3 git

echo "Creating default nginx configuration..."
sudo tee /etc/nginx/nginx.conf > /dev/null <<EOL
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                      '\$status \$body_bytes_sent "\$http_referer" '
                      '"\$http_user_agent" "\$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;
    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_names_hash_bucket_size 128;
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
    server {
        listen 80 default_server;
        server_name _;
        root /usr/share/nginx/html;
        location / {
            try_files \$uri \$uri/ =404;
        }
    }
    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    proxy_read_timeout 600;
    send_timeout 600;
}
EOL

echo "Navigating to project directory..."
cd /home/ec2-user/web-scraper-api

echo "Creating and activating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Upgrading pip and installing requirements..."
pip3 install --upgrade pip
pip3 install -r requirements.txt
pip3 install gunicorn

echo "Setting Flask environment variables..."
export FLASK_APP=app.py
export FLASK_ENV=production

echo "Creating Gunicorn systemd service file..."
sudo tee /etc/systemd/system/web-scraper.service > /dev/null <<EOL

[Unit]
Description=Gunicorn instance to serve Flask web scraper
After=network.target

[Service]
User=ec2-user
Group=nginx
WorkingDirectory=/home/ec2-user/web-scraper-api
Environment="PATH=/home/ec2-user/web-scraper-api/venv/bin"
ExecStart=/home/ec2-user/web-scraper-api/venv/bin/gunicorn --workers 3 --bind unix:/home/ec2-user/web-scraper-api/web-scraper.sock -m 007 --log-file /home/ec2-user/web-scraper-api/gunicorn.log --log-level debug --timeout 3600 app:app

[Install]
WantedBy=multi-user.target
EOL

echo "Reloading systemd to apply the new service..."
sudo systemctl daemon-reload

echo "Starting and enabling Gunicorn service..."
sudo systemctl start web-scraper.service
sudo systemctl enable web-scraper.service

echo "Configuring Nginx for Flask application..."
sudo tee /etc/nginx/conf.d/web-scraper.conf > /dev/null <<'EOL'
server {
    listen 80;
    server_name $INSTANCE_DNS;

    location / {
        proxy_pass http://unix:/home/ec2-user/web-scraper-api/web-scraper.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

echo "Testing Nginx configuration..."
sudo nginx -t

echo "Restarting and enabling Nginx..."
sudo systemctl restart nginx
sudo systemctl enable nginx

# Ensure the Nginx user has access to the Gunicorn socket
sudo chown ec2-user:nginx /home/ec2-user/web-scraper-api/web-scraper.sock
sudo chmod 660 /home/ec2-user/web-scraper-api/web-scraper.sock

# Restart Gunicorn and Nginx services
echo "Restarting Gunicorn and Nginx services..."
sudo systemctl restart web-scraper.service
sudo systemctl restart nginx

# Ensure permissions
chmod 755 /home/ec2-user
chmod 755 /home/ec2-user/web-scraper-api
sudo usermod -aG ec2-user nginx

EOF

echo "Deployment to EC2 instance completed successfully"
