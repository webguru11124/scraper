## Flask-selenium-scraper

This project is designed to scrape data from a specified website using Selenium and store the data in a PostgreSQL database. It uses AWS services such as EC2, RDS, Lambda, and Secrets Manager for infrastructure, and it leverages Flask for the web application.

### Project Structure

```
django-selenium-scraper/
├── cdk-infra/
│   ├── app.py
│   ├── cdk_infra/
│   │   ├── __init__.py
│   │   └── cdk_infra_stack.py
│   └── requirements.txt
├── lambda/
│   ├── lambda_function.py
├── web-scraper-api/
│   ├── app.py
│   ├── init_db.sql
│   ├── requirements.txt
├── .gitignore
├── deploy.sh
├── package.json
└── README.md
```

### Setup Instructions

#### Prerequisites

- Python 3.x
- AWS CLI configured with appropriate permissions
- Node.js and npm (for AWS CDK)

#### Installation

1. **Clone the repository**

```sh
git clone https://github.com/webguru11124/scraper.git
cd scraper
```

2. **Install dependencies**

```sh
npm install
python3 -m venv venv
source venv/bin/activate
pip install -r web-scraper-api/requirements.txt
pip install -r cdk-infra/requirements.txt
```

3. **Deploy the infrastructure**

```sh
npm run deploy-infra
```

4. **Deploy the web scraper API**

```sh
npm run deploy-api
```

5. **Local Development**

```sh
npm run dev
```

### Usage

deployed url

curl http://ec2-13-60-71-122.eu-north-1.compute.amazonaws.com/scrape?last_name=Donna or
curl http://ec2-13-60-71-122.eu-north-1.compute.amazonaws.com/scrape

### Challenge

**Scraping the College of Opticians Website**:

- **Task**: Scrape paginated data from the College of Opticians website (https://members.collegeofopticians.ca/Public-Register).
- **Steps**:
  1. **Navigate to the Website**: Use Selenium to open the public register page.
  2. **Handle Pagination**:
     - Locate the "Next Page" button using a CSS selector.
     - Click the "Next Page" button to load the next set of data.
     - Determine if it is the last page by checking the "onclick" value or the button's disabled state.
  3. **Extract Data**: Extract the necessary data from each page and store it in a PostgreSQL database.
  4. **Set Search Queries**: Allow search queries to be passed from the API request event to Selenium for dynamic data extraction.

**Deployment Configuration**:

- **Infrastructure Setup**: Configure the CDK stack for deployment, including setting up EC2, RDS, and other required AWS resources.
- **Server Configuration**:
  - **SSH Key Management**: Ensure proper SSH key management for secure access to the EC2 instance.
  - **Gunicorn and Nginx**: Install and configure Gunicorn and Nginx to deploy the Flask application.
  - **Troubleshooting**:
    - **502 Bad Gateway Error**: Resolve issues in the Nginx configuration file that cause 502 errors.
    - **500 Internal Server Error**: Address frequent 500 errors by increasing the Gunicorn timeout setting from 30 seconds to a more appropriate value for long-running requests (e.g., 1200 seconds).

**CI/CD Configuration**:

- **Automated Deployment**:
  - Create a CI/CD pipeline using GitHub Actions to automate the deployment process.
  - Store and use environment variables and secrets securely using AWS Secrets Manager or Parameter Store.
- **Logging and Monitoring**: Implement comprehensive logging to diagnose and fix issues promptly.
- **Error Handling**: Ensure robust error handling in the Flask application to provide informative error messages and improve debugging.

### Usage

After deploying, you can access the Flask API on the EC2 instance's public DNS. The `/scrape` endpoint will trigger the web scraping and store the data in the RDS database.

### Further Improvements

1. **Use Django**:
   - Refactor the project to use Django instead of Flask for the web application.
   - Implement database interactions directly in the Django application, removing the need for a Lambda function.

2. **Pass Environment Variables to Django**:
   - Ensure all necessary environment variables like database env are securely passed to the Django application using AWS Secrets Manager or Parameter Store.

3. **Automate Infrastructure Deployment**:
   - Create a separate CI/CD pipeline for deploying infrastructure changes automatically using GitHub Actions.

4. **Containerize the Application**:
   - Create a Dockerfile for the Django or Flask application.
   - Build and push the Docker image to Amazon ECR.
   - Deploy the application using ECS or another container orchestration service.

5. **Extensive Testing**:
   - Add more comprehensive tests for both the web scraper and the web application.
   - Implement unit tests, integration tests, and end-to-end tests.

### Example Dockerfile for Django Application

```Dockerfile
# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/

# Run server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "django_selenium_scraper.wsgi:application"]
```

### CI/CD for Infrastructure

Create a new GitHub Actions workflow file `.github/workflows/deploy-infra.yml`:

```yaml
name: Deploy Infrastructure

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v2

    - name: Set up Node.js
      uses: actions/setup-node@v2
      with:
        node-version: '14'

    - name: Install dependencies
      run: npm install

    - name: Deploy CDK Stack
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      run: |
        cd cdk-infra
        npx cdk deploy --outputs-file output.json --require-approval=never --all
```

### Conclusion

By following these steps and suggestions, you can enhance the functionality, maintainability, and scalability of your project. If you have any questions or need further assistance, feel free to reach out.