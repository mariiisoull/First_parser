import csv
import json
import re
import time  # Для добавления задержки
import requests
from bs4 import BeautifulSoup

BASE_URL = 'https://mashina.kg/'


def get_soup_with_retry(url: str, max_retries: int = 3) -> BeautifulSoup | None:

    # User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Запрос к {url} (Попытка {attempt}/{max_retries})...")

            #   TIMEOUT
            response = requests.get(url, headers=headers, timeout=5)

            # Проверяем статус-код #200
            response.raise_for_status()

            return BeautifulSoup(response.text, 'html.parser')

        except requests.exceptions.Timeout:
            print(
                f"[Ошибка] Превышено время ожидания (Timeout) при запросе к {url}."
            )
        except requests.exceptions.HTTPError as http_err:
            print(f"[Ошибка HTTP] Сервер вернул ошибку: {http_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"[Ошибка сети] Не удалось связаться с сервером: {req_err}")

        # Если ошибка, ждем 
        if attempt < max_retries:
            sleep_time = 3
            print(f"Ожидание {sleep_time} сек. перед повторным запросом...")
            time.sleep(sleep_time)

    print(
        f"[Критическая ошибка] Не удалось получить данные с {url} после {max_retries} попыток."
    )
    return None

#ОЧистка данных
def clean_price(price_str: str) -> int | None:
    
    if not price_str:
        return None
    # Только цифры
    cleaned = re.sub(r'\D', '', price_str)
    try:
        return int(cleaned) if cleaned else None
    except ValueError:
        return None

#Извлекает и очищает данные из найденных карточек
def parse_cards(cards) -> list:
    
    parsed_data = []

    for card in cards:
        try:
            # 1. Название (h3)
            title_el = card.find(
                'h3', class_='text-[13px] leading-5 text-text-primary'
            )
            title = title_el.text.strip() if title_el else None

            # 2. Цена (span)
            price_el = card.find(
                'span',
                class_='text-sm font-medium leading-5 text-text-primary whitespace-nowrap',
            )
            price_raw = price_el.text.strip() if price_el else None
            price = clean_price(price_raw)

            # 3. Дополнительные характеристики (p)
            specs_el = card.find(
                'p', class_='text-xs leading-4 text-text-secondary line-clamp-2'
            )
            specs = specs_el.text.strip() if specs_el else None
            if specs:
                # Очищаем от лишних внутренних пробелов и переносов строк
                specs = ' '.join(specs.split())

            # 4. Ссылка
            link_el = card.find('a', class_='block') or card.find_parent(
                'a', class_='block'
            )
            if link_el and link_el.has_attr('href'):
                href = link_el['href']
                #
                link = (
                    href
                    if href.startswith('http')
                    else 'https://mashina.kg' + href
                )
            else:
                link = None

            parsed_data.append(
                {'title': title, 'price': price, 'specs': specs, 'link': link}
            )

        except Exception as e:
            # Проверка подленности карточки
            print(f"[Предупреждение] Ошибка при парсинге карточки: {e}")
            continue

    return parsed_data

#  Удаление дубликатов
def remove_duplicates(data: list) -> list:
   
    seen_links = set()
    unique_data = []
    for item in data:
        if item['link'] not in seen_links:
            if item['link']:
                seen_links.add(item['link'])
            unique_data.append(item)
    return unique_data

#  СОХРАНЕНИЕ В ФАЙЛЫ
def save_results(data: list):
    
    if not data:
        print('Сохранение отменено: нет данных для записи.')
        return

    try:
        # Сохраняем в CSV
        with open('result.csv', mode='w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print('Данные успешно сохранены в result.csv')
    except Exception as e:
        print(f'[Ошибка] Не удалось сохранить CSV-файл: {e}')

    try:
        # Сохраняем в JSON
        with open('result.json', mode='w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print('Данные успешно сохранены в result.json')
    except Exception as e:
        print(f'[Ошибка] Не удалось сохранить JSON-файл: {e}')


def main():
    # безопасный запрос
    soup = get_soup_with_retry(BASE_URL)

    if not soup:
        print('[Ошибка] Не удалось получить BeautifulSoup объект. Завершение работы.')
        return

    tag = 'div'
    classcard = 'card_content p-(--card-content-padding) pt-0 flex flex-col gap-2 p-0! pb-4! pt-3!'

    #  Ищем карточки
    print('Поиск карточек на странице...')
    cards = soup.find_all(tag, {'class': classcard})
    print(f'Найдено карточек на странице: {len(cards)}')

    if not cards:
        print(
            '[Внимание] Карточки не найдены. Возможно, изменились классы на сайте.'
        )
        return

    # Добавляем небольшую задержку перед началом парсинга
    time.sleep(1)

    print('Извлечение данных из карточек...')
    raw_cars_data = parse_cards(cards)
    print(f'Успешно обработано объявлений: {len(raw_cars_data)}')

    # Очищаем от дубликатов
    cleaned_cars_data = remove_duplicates(raw_cars_data)
    print(f'Количество уникальных объявлений: {len(cleaned_cars_data)}')

   
    save_results(cleaned_cars_data)


if __name__ == '__main__':
    main()