from bs4 import BeautifulSoup as bs
import aiohttp
import re
from functools import reduce
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By

MOSCOW_PHONE_CODE = '495'
TASK_LIMIT = 5
        
async def get_phone_numbers(url: str, path_to_contacts: str | list[str]) -> list:
    
    """Парсит HTML по заданному адресу сайта и пути(-ям) к странице контактов"""
    
    path_to_contacts = path_to_contacts if type(path_to_contacts) is list else [path_to_contacts]
    phone_pattern = re.compile('[8]{1}[ -]{1}[(]?\d{3}[)]?[ -]{1}\d{3}[ -]{1}\d{2}[ -]{1}\d{2}')
    
    async with aiohttp.ClientSession(trust_env=True) as session:
        html_pages = await asyncio.ensure_future(fetch_many(url, path_to_contacts, session))

    phone_list = await parse_many(html_pages, phone_pattern)
    
    return url, phone_list
        
async def fetch(url: str, session: aiohttp.ClientSession) -> str:
    
    """Получает нужную страницу по URI с использованием GET запроса по созданной сессии"""
    
    async with session.get(url) as response:
        return await response.text()
    
async def fetch_with_sem(url: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> str:
    
    """Получает нужную страницу с использованием ограничения на таски"""
    
    async with semaphore:
        return await fetch(url, session)
    
async def fetch_many(url, pages, session) -> asyncio.Future[list]:
    
    """Получает несколько страниц с сайта асинхронно"""
    
    tasks = []
    sem = asyncio.Semaphore(TASK_LIMIT)
    
    for page in pages:
        URI = url + page
        task = asyncio.ensure_future(fetch_with_sem(URI, session, sem))
        tasks.append(task)
    
    return await asyncio.gather(*tasks)

async def parse(html_page: str, phone_pattern: re.Pattern, semaphore: asyncio.Semaphore):
    
    """Парсинг одной страницы"""
    
    phone_class_pattern = re.compile('phone')
    async with semaphore:
        soup = bs(html_page, 'html.parser')
        div_phone_el = soup.find('div', attrs={'class': phone_class_pattern})
        
        if div_phone_el is not None:
            phone = convert_phone_format(div_phone_el.text)
            
            if phone is None:
                # Если в тексте элемента не было найдено нужное значение телефона
                # то парсим весь документ
                phone_match = re.search(phone_pattern, html_page)
            else:
                return phone
        else:
            # Если не находим div с нужным названием класса то ищем по всей странице
            phone_match = re.search(phone_pattern, html_page)
            
        if phone_match is None:
            # Если совпадение не было найдено по всей странице
            # пытаемся запустить браузер и выбрать нужный элемент страницы
            # с подгруженным JS (Как это сделано на https://hands.ru)
            browser = webdriver.Chrome()
            browser.get('https://hands.ru/company/about')
            browser.find_element(By.CSS_SELECTOR, '#root > div > footer > div > div.footer__block.footer__block_phone > button').click()
            phone_match = re.search(phone_pattern, browser.page_source)
            
        return convert_phone_format(phone_match.group(0))

async def parse_many(html_pages: list[str], phone_pattern: re.Pattern):
    
    """Парсим несколько страниц за раз"""
    
    tasks = []
    sem = asyncio.Semaphore(TASK_LIMIT)

    for html in html_pages:
        task = asyncio.ensure_future(parse(html, phone_pattern, sem))
        tasks.append(task)
        
    return await asyncio.gather(*tasks)

def convert_phone_format(phone: str) -> str:
    
    """Перевести телефон со страницы в только численный формат"""
    
    phone_symbols = [*filter(str.isdigit, phone)]
                
    if phone_symbols.__len__() == 0:
        return None
    elif phone_symbols.__len__() == 8:
        # Если был указан телефон без кода региона
        # вставляем после 8 телефонный код Москвы
        phone_symbols.insert(1, MOSCOW_PHONE_CODE)
    
    res_phone = reduce(lambda i, j: i + j, phone_symbols, '')
    
    # Предполагаю, что необходимо хранить телефон в базе как строку,
    # если необходимо хранить как int значение -> раскомментировать:
    # res_phone = int(res_phone)
    
    return res_phone