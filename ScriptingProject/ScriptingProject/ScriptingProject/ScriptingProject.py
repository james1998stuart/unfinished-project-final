import requests
from datetime import datetime
from bs4 import BeautifulSoup

#list of crafting methods with required levels
crafting_methods = [
    {"name": "Spin flax into bowstring", "level": 10},
    {"name": "Cut sapphire", "level": 20},
    {"name": "Make emerald ring", "level": 27},
    {"name": "Blow molten glass into orbs", "level": 46},
    {"name": "Craft fire battlestaff", "level": 63},
    {"name": "Craft air battlestaff", "level": 66},
    {"name": "Craft amulet of glory", "level": 80},
    {"name": "Make black d'hide body", "level": 84},
]


#fetches item prices based on their ids
def get_item_price(item_id):
    url = f"https://prices.runescape.wiki/api/v1/osrs/latest?id={item_id}"
    headers = {'User-Agent': 'osrs-price-checker-lil-bro/1.0'}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch price data: {response.status_code}")

    data = response.json()
    return data['data'][str(item_id)]

#finds the difference in price between two items
def compare_item_prices(item1_id, item2_id, item1_name="Item 1", item2_name="Item 2"):
    item1 = get_item_price(item1_id)
    item2 = get_item_price(item2_id)

    item1_price = item1.get('high', 0)
    item2_price = item2.get('high', 0)

    difference = item1_price - item2_price

    print(f"🪙 {item1_name}: {item1_price} gp")
    print(f"🪙 {item2_name}: {item2_price} gp")
    print(f"Price Difference: {abs(difference)} gp ({'Item 1 is more' if difference > 0 else 'Item 2 is more'})")

    return difference

#fetches the users crafting level
def get_crafting_level(username):
    sanitized_username = username.replace(" ", "_")
    url = f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={sanitized_username}"
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Could not fetch hiscores for '{username}'")
        return None

    lines = response.text.strip().split("\n")

    try:
        crafting_line = lines[13]  # Crafting is the 14th skill (0-based index)
        rank, level, xp = crafting_line.split(",")
        print(f"\n {username.title()}'s Crafting Level: {level}")
        print(f" XP: {int(xp):,}")
        print(f" Rank: {int(rank):,}")
        return int(level)
    except (IndexError, ValueError):
        print("Could not extract crafting data.")
        return None

def get_unlocked_methods(crafting_level):#returns unlocked crafting methods
    return [m["name"] for m in crafting_methods if crafting_level >= m["level"]]

def log_data(username, level, unlocked_methods): #logs data
    with open("crafting_log.txt", "a") as log_file:
        log_file.write(f"\n[{datetime.now()}] Username: {username}, Crafting Level: {level}\n")
        for method in unlocked_methods:
            log_file.write(f" - {method}\n")

def get_item_id_map():#helper that gets the item ID map
    url = "https://prices.runescape.wiki/api/v1/osrs/mapping"
    headers = {"User-Agent": "osrs-crafting-calc/1.0"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Failed to fetch item ID map")
        return {}
    data = response.json()
    return {item["name"].lower(): item["id"] for item in data}

def get_all_crafting_methods(user_level): #returns all unlocked crafting methods by scraping the wiki API
    url = "https://oldschool.runescape.wiki/w/Crafting"
    headers = {"User-Agent": "osrs-crafting-calc/1.0"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Failed to fetch crafting methods.")
        return []

    id_map = get_item_id_map()

    soup = BeautifulSoup(response.content, "html.parser")
    tables = soup.find_all("table", class_="wikitable")
    methods = []

    for table in tables:
        rows = table.find_all("tr")[1:]  # Skip header
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                try:
                    level_text = cols[0].text.strip()
                    if not level_text.isdigit():
                        continue  # skip non-numeric entries like quests

                    level_required = int(level_text)
                    link = cols[2].find("a")
                    item_name = link.text.strip() if link else cols[2].text.strip()
                    item_id = id_map.get(item_name.lower())

                    if not item_id:
                        continue  # skip if we can't find a valid ID

                    if level_required <= user_level:
                        methods.append({
                            "name": item_name,
                            "level": level_required,
                            "id": item_id
                        })

                except Exception as e:
                    print("Error parsing row:", e)
                    continue

    return methods

def get_required_materials(item_name):
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "osrs-crafting-calc/1.0"}
    materials = {}

    # Step 1: Try API
    api_url = "https://oldschool.runescape.wiki/api.php"
    params = {
        "action": "cargoquery",
        "tables": "item_materials",
        "fields": "material,quantity",
        "where": f'item="{item_name}"',
        "format": "json"
    }

    try:
        api_response = requests.get(api_url, params=params, headers=headers)
        if api_response.status_code == 200:
            data = api_response.json()
            for entry in data.get("cargoquery", []):
                m = entry["title"]["material"]
                q = int(entry["title"]["quantity"])
                materials[m] = q
            if materials:
                print(f"📦 API materials for {item_name}: {materials}")
                return materials
    except Exception as e:
        print(f"⚠️ API error for {item_name}: {e}")

    # Step 2: Fallback to web scraping
    url_name = item_name.replace(" ", "_")
    scrape_url = f"https://oldschool.runescape.wiki/w/{url_name}"

    try:
        scrape_response = requests.get(scrape_url, headers=headers)
        if scrape_response.status_code != 200:
            print(f"❌ Failed to fetch page for {item_name}")
            return {}

        soup = BeautifulSoup(scrape_response.content, "html.parser")
        creation_header = soup.find("span", id="Creation")
        if not creation_header:
            print(f"❌ No 'Creation' section for {item_name}")
            return {}

        table = creation_header.find_parent().find_next("table", class_="wikitable")
        if not table:
            print(f"❌ No wikitable found for {item_name}")
            return {}

        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            last_td = cols[-1]
            links = last_td.find_all("a")

            for link in links:
                name = link.get("title")
                if not name or name.lower() in ("furnace", "none"):
                    continue

                qty = 1
                qty_text = link.previous_sibling
                if qty_text:
                    try:
                        qty = int(qty_text.strip().split("×")[0])
                    except:
                        pass

                materials[name.strip()] = qty

        if materials:
            print(f"🔍 Scraped materials for {item_name}: {materials}")
        else:
            print(f"❌ No materials found via API or scraping for {item_name}")

    except Exception as e:
        print(f"⚠️ Scrape error for {item_name}: {e}")

    return materials


def calculate_profit(item, id_map, ge_prices): #calculates the profit based on ge prices of a crafting recipe
    item_name = item["name"]
    item_id = item["id"]

    if str(item_id) not in ge_prices:
        return None

    output_price = ge_prices[str(item_id)]["low"]
    materials = get_required_materials(item_name)

    total_cost = 0
    for mat_name, qty in materials.items():
        mat_id = id_map.get(mat_name.lower())
        if not mat_id or str(mat_id) not in ge_prices:
            return None
        cost = ge_prices[str(mat_id)]["high"] * qty
        total_cost += cost

    return {
        "name": item_name,
        "level": item["level"],
        "price": output_price,
        "cost": total_cost,
        "profit": output_price - total_cost
    }

def build_item_name_to_id():
    import requests

    url = "https://prices.runescape.wiki/api/v1/osrs/mapping"
    headers = {"User-Agent": "osrs-crafting-calc/1.0"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to fetch item mapping data.")

    item_map = {}
    for item in response.json():
        name = item["name"]
        item_id = item["id"]
        item_map[name] = item_id

    print(f"✅ Loaded {len(item_map)} item name → ID mappings.")
    return item_map

#main of course
def main():
    username = input("Enter RS username: ")
    level = get_crafting_level(username)

    if level is None:
        print("Could not fetch crafting level.")
        return

    print(f"\n{username.title()}'s Crafting Level: {level}")

    # Get item ID map + GE prices
    id_map = get_item_id_map()
    ge_prices = requests.get("https://prices.runescape.wiki/api/v1/osrs/latest").json()["data"]

    # Get unlocked craftable items
    unlocked = get_all_crafting_methods(level)

    print(f"\nUnlocked Crafting Methods ({len(unlocked)}):\n")

    for item in unlocked:
        result = calculate_profit(item, id_map, ge_prices)
        if result:
            print(f"🧪 {result['name']} (Lvl {result['level']}): +{result['profit']} gp "
                f"[Sell: {result['price']} | Cost: {result['cost']}]")
        else:
            print(f"⚠️ Skipped: {item['name']} (missing materials or prices)")

if __name__ == "__main__":
    main()

    #So far, I have a function that looks up an items price based off of the osrs API, and '
    # compareS it's price to another item
    #This will be used to determine the profit of a crafted item in the future
    #I also have a function that determines a users crafting level'
    #and a function that determines which crafts the user can create at their level
    #I found that it was too difficult to use the wiki's API for now (NOT THE OSRS API)
    #I essentially would have had to scrape a web page using a regex command to find the xp for each item
    #for now I hard coded the xp values for the items
    #I'm going to change this in the future
    #I'd also like to save some of this data to a local drive, allowing the user to have saved profiles
    #for different users

    