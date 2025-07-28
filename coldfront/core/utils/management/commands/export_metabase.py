from django.core.management.base import BaseCommand, CommandError
import requests
import json

from coldfront.core.utils.metabase_utils import get_card_details, get_collection_id, get_collection_items

class Command(BaseCommand):
    help = 'Export Metabase cards from a collection using API key'

    def add_arguments(self, parser):
        parser.add_argument(
            '--key',
            type=str,
            required=True,
            help='Metabase API key'
        )
        parser.add_argument(
            '--collection',
            type=str,
            default='Savio Analytics',
            help="Metabase collection name (default: 'Savio Analytics')"
        )
        parser.add_argument(
            '--url',
            type=str,
            default='http://metabase:3000/api',
            help="Base URL for the Metabase API (default: 'http://metabase:3000/api')"
        )

    def handle(self, *args, **options):
        API_KEY = options['key']
        collection_name = options['collection']

        if not API_KEY:
            raise CommandError('Please provide the API key using --key')

        HEADERS = {
            'x-api-key': API_KEY
        }

        collection_id = get_collection_id(collection_name, HEADERS, options['url'])

        items = get_collection_items(collection_id, HEADERS, options['url'])['data']

        cards = [get_card_details(item['id'], HEADERS, options['url']) for item in items]

        # Keep only the info needed to re-generate the cards
        cards = [
            {
                'visualization_settings': card['visualization_settings'],
                'dataset_query': card['dataset_query'],
                'parameter_mappings': card['parameter_mappings'],
                'name': card['name'],
                'type': card['type'],
                'display': card['display'],
                'parameters': card['parameters'],
                'description': card['description']
            }
            for card in cards
        ]

        # Step 5: Output to file
        output_file = f'{collection_name}_export.json'
        with open(output_file, 'w') as f:
            json.dump(cards, f, indent=2)
        print(f'Exported {len(cards)} cards to {output_file}')
