from django.http import JsonResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

def scrape(request):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    driver.get('https://members.collegeofopticians.ca/Public-Register')

    # Implement your scraping logic here
    data = driver.find_element_by_tag_name('body').text  # Example

    driver.quit()
    return JsonResponse({'data': data})
