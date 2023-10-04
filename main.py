from web_parser import get_phone_numbers
import asyncio
from time import time

DEBUG = True

if DEBUG:
    # В проде данные значения должны браться
    # из базы данных по созданному подключению
    # key: URL, value: path
    test_cases = {
        'https://www.tinkoff.ru': ['/about', '/cards/credit-cards'],
        'https://hands.ru': '/company/about',
        'https://repetitors.info': '/',
        'https://5ka.ru': '/about/',
    }
    
async def main():
    tasks = []
    
    for url, path in test_cases.items():
        tasks.append(asyncio.ensure_future(get_phone_numbers(url, path)))
        
    return await asyncio.gather(*tasks)

if __name__ == '__main__':
    start = time()
    
    total_phones = {
        el[0]: el[1:]
        for el in asyncio.run(main())
    }
    
    end = time()
    print(f'Total phones: {total_phones}\nTotal time: {end - start} s')
    print('''\n\t* Для https://www.tinkoff.ru найдено 2 одинаковых телефона,
          так как я выбрал 2 страницы с одинаковыми телефонами в конце странице
          для показа функциональности поиска по списку из нужных страниц.
          При необходимости можно проверять список на дубликаты и удалять их.
          ''')