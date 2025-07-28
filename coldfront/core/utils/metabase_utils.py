import json
import requests

METABASE_URL = 'http://metabase:3000/api'

def get_collection_id(collection_name, headers, url=METABASE_URL):
    url = f'{url}/collection'
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    collections = res.json()
    for col in collections:
        if col['name'] == collection_name:
            return col['id']
    raise f"Collection '{collection_name}' not found."

def get_collection_items(collection_id, headers, url=METABASE_URL):
    url = f'{url}/collection/{collection_id}/items'
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()

def get_card_details(card_id, headers, url=METABASE_URL):
    url = f'{url}/card/{card_id}'
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()

def create_card(card_data, collection_id, headers, force=False, url=METABASE_URL):
    if not force:
        # Check if card already exists
        existing_cards = get_collection_items(collection_id, headers)
        for existing_card in existing_cards['data']:
            if existing_card['name'] == card_data['name']:
                return {"exists": True, "id": existing_card['id']}
    payload = card_data.copy()
    payload['collection_id'] = collection_id
    url = f'{url}/card'
    res = requests.post(url, headers=headers, data=json.dumps(payload))
    res.raise_for_status()
    return res.json()
