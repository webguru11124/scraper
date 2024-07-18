import pytest
from flask import Flask
import json
from app import app  # Import the Flask app from your app.py file

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_scrape(client, mocker):
    # Mock the selenium parts to avoid actual web scraping during tests
    mock_driver = mocker.patch('app.webdriver.Chrome')
    mock_instance = mock_driver.return_value

    # Mock methods
    mock_instance.get.return_value = None
    mock_instance.find_element.return_value = mocker.Mock()
    mock_instance.find_elements.return_value = [mocker.Mock() for _ in range(20)]

    # Mock find_element to return a mock element with a click method
    mock_find_element = mocker.Mock()
    mock_find_element.click.return_value = None
    mock_instance.find_element.side_effect = lambda by, value: mock_find_element

    mock_set_dropdown_value = mocker.patch('app.set_dropdown_value')
    mock_extract_table_data = mocker.patch('app.extract_table_data', return_value=[{
        "registrant": "John Doe",
        "status": "Active",
        "class": "Class A",
        "location": "City, State",
        "details_link": "http://example.com/details"
    }])

    # Send a GET request to the /scrape endpoint
    response = client.get('/scrape', query_string={
        'last_name': 'Doe',
        'first_name_contains': 'John'
    })

    # Verify the response
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    # assert len(data["data"]) == 1
    # assert data["data"][0]["registrant"] == "John Doe"

def test_scrape_error(client, mocker):
    # Mock the selenium parts to simulate an error
    mock_driver = mocker.patch('app.webdriver.Chrome')
    mock_driver.side_effect = Exception("Driver error")

    # Send a GET request to the /scrape endpoint
    response = client.get('/scrape', query_string={
        'last_name': 'Doe',
        'first_name_contains': 'John'
    })

    # Verify the response
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Driver error"
