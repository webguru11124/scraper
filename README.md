
# Django Selenium Scraper

This project is a web scraping application built with Django, Selenium, and AWS. It scrapes data from a specified website and stores it in a PostgreSQL database hosted on AWS RDS. The application is deployed on an AWS EC2 instance, and the scraping tasks are scheduled using AWS Lambda and CloudWatch Events. The infrastructure is managed using AWS CDK.

## Project Structure

```
django-selenium-scraper/
├── .github/
│   └── workflows/
│       └── deploy.yml
├── cdk-infra/
│   ├── lambda/
│   │   └── lambda_function.py
│   ├── cdk_infra/
│   │   ├── __init__.py
│   │   └── cdk_infra_stack.py
│   ├── app.py
│   ├── cdk.json
│   ├── requirements.txt
│   └── README.md
├── scraper_project/
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── tests/
│   │   │   └── test_views.py
│   │   ├── views.py
│   ├── scraper_project/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── manage.py
├── .flake8
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- AWS CLI
- AWS CDK
- Python 3.8

### Setting Up the Django Project

1. Create and activate a virtual environment:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Run the Django development server:

    ```bash
    python manage.py runserver
    ```

### Running Lint, Format, and Tests

1. Lint the code with `flake8`:

    ```bash
    flake8 .
    ```

2. Format the code with `black`:

    ```bash
    black .
    ```

3. Run tests with `pytest`:

    ```bash
    pytest
    ```

### Deploying to AWS with CDK

1. Install the required CDK dependencies:

    ```bash
    pip install

 -r cdk-infra/requirements.txt
    ```

2. Bootstrap and deploy the CDK stack:

    ```bash
    cd cdk-infra
    cdk bootstrap
    cdk deploy
    ```

### Setting Up CI/CD with GitHub Actions

Create a `.github/workflows/deploy.yml` file with the following content to set up CI/CD:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.x'

    - name: Install dependencies
      run: |
        python -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt

    - name: Lint with flake8
      run: |
        source venv/bin/activate
        flake8 .

    - name: Format with black
      run: |
        source venv/bin/activate
        black --check .

    - name: Test with pytest
      run: |
        source venv/bin/activate
        pytest

    - name: Deploy to EC2
      if: success()
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        EC2_INSTANCE_ID: ${{ secrets.EC2_INSTANCE_ID }}
        KEY_PATH: ${{ secrets.KEY_PATH }}
        EC2_PUBLIC_DNS: ${{ secrets.EC2_PUBLIC_DNS }}
      run: |
        scp -i $KEY_PATH -r . ec2-user@$EC2_PUBLIC_DNS:/home/ec2-user/web-scraper-api
        ssh -i $KEY_PATH ec2-user@$EC2_PUBLIC_DNS 'cd /home/ec2-user/web-scraper-api && python3 manage.py migrate && python3 manage.py runserver 0.0.0.0:80'
```

## License

This project is licensed under the MIT License.

By following these steps and including the provided configuration files, you will have a Django and Selenium project with linting, formatting, and testing integrated, as well as a CI/CD pipeline set up to ensure code quality and smooth deployments.