import logging
import re

import requests

logger = logging.getLogger(__name__)


def fetch_price_sync(market_hash_name):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }

    url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=5&market_hash_name={market_hash_name}"

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                price_str = data.get("median_price") or data.get("lowest_price")
                if price_str:
                    logger.debug(
                        f"Original price string for {market_hash_name}: {price_str}"
                    )

                    # Используем регулярное выражение для извлечения только цифр, запятых и точек
                    price_str = re.sub(r"[^0-9,.]", "", price_str)
                    logger.debug(f"Cleaned price string: {price_str}")

                    if "," in price_str:
                        # Если есть запятая, заменяем её на точку
                        price_str = price_str.replace(",", ".")

                    # Удаляем точку в конце, если она есть
                    price_str = price_str.rstrip(".")

                    logger.debug(f"Final price string before conversion: {price_str}")

                    # Конвертируем в число
                    price = float(price_str)

                    # Если цена больше 1000, вероятно она в копейках
                    if price > 1000 and "," not in price_str:
                        price = price / 100

                    logger.debug(f"Final price: {price}")
                    return price
        return None
    except Exception as e:
        logger.error(f"Error fetching price for {market_hash_name}: {e}")
        return None


def fetch_all_prices_sync(market_hash_names):
    prices = []
    for name in market_hash_names:
        price = fetch_price_sync(name)
        prices.append(price)
    return prices


# RUST - 252490
def get_steam_inventory(steam_id, game_id="730"):
    url = f"https://steamcommunity.com/inventory/{steam_id}/{game_id}/2"
    try:
        response = requests.get(url)
        logger.info(f"Steam API Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logger.info(f"Received inventory data: {bool(data)}")
            return data
        else:
            logger.error(
                f"Failed to get inventory. Status code: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.error(f"Error getting inventory: {str(e)}")
        return None


def parse_inventory_items(inventory_data):
    if not inventory_data:
        logger.error("No inventory data provided")
        return []

    if "assets" not in inventory_data or "descriptions" not in inventory_data:
        logger.error("Invalid inventory data structure")
        return []

    try:
        items = []
        assets = inventory_data["assets"]
        descriptions = {
            f"{d['classid']}_{d['instanceid']}": d
            for d in inventory_data["descriptions"]
        }

        market_names = []
        tradable_items = {}  # Словарь для хранения tradable предметов | потом на Redis

        # Сначала собираем только tradable предметы
        for asset in assets:
            key = f"{asset['classid']}_{asset['instanceid']}"
            if key in descriptions:
                description = descriptions[key]
                # Проверяем, является ли предмет tradable
                if description.get("tradable", 0) == 1:
                    market_name = description.get("market_name", "")
                    if market_name:
                        market_names.append(market_name)
                        tradable_items[market_name] = (asset, description)

        # Получаем цены только для tradable предметов
        prices = fetch_all_prices_sync(market_names)
        price_dict = dict(zip(market_names, prices))

        # Создаем список предметов только из tradable вещей
        for market_name, (asset, description) in tradable_items.items():
            price = price_dict.get(market_name)
            if price is not None:
                formatted_price = f"{price:.2f} ₽"
            else:
                formatted_price = "Not Found"

            item = {
                "asset_id": asset["assetid"],
                "name": description.get("name", ""),
                "market_name": market_name,
                "icon_url": f"https://steamcommunity-a.akamaihd.net/economy/image/{description.get('icon_url', '')}",
                "tradable": description.get("tradable", 0),
                "marketable": description.get("marketable", 0),
                "type": description.get("type", ""),
                "wear": next(
                    (
                        tag.get("name")
                        for tag in description.get("tags", [])
                        if tag.get("category") == "Exterior"
                    ),
                    None,
                ),
                "rarity": next(
                    (
                        tag.get("name")
                        for tag in description.get("tags", [])
                        if tag.get("category") == "Rarity"
                    ),
                    None,
                ),
                "price": formatted_price,
            }
            items.append(item)

        return items
    except Exception as e:
        logger.error(f"Error parsing inventory items: {str(e)}")
        return []
