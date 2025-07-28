from django.core.management.base import BaseCommand, CommandError
import json
import os

from coldfront.core.utils.metabase_utils import create_card, get_collection_id

class Command(BaseCommand):
    help = "Import Metabase cards from a JSON file into a specific collection"

    def add_arguments(self, parser):
        parser.add_argument(
            "--key",
            type=str,
            required=True,
            help="Metabase API key"
        )
        parser.add_argument(
            "--collection",
            type=str,
            default="Savio Analytics",
            help="Metabase collection name (default: 'Savio Analytics')"
        )
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to JSON file with exported card metadata"
        )
        parser.add_argument(
            "--url",
            type=str,
            default="http://metabase:3000/api",
            help="Base URL for the Metabase API (default: 'http://metabase:3000/api')"
        )
        parser.add_argument(
            "--force",
            action='store_true',
            help="Force creation of cards even if they already exist (default: False)"
        )

    def handle(self, *args, **options):
        API_KEY = options["key"]
        collection_name = options["collection"]
        file_path = options["file"]

        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")

        HEADERS = {
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }


        # Load exported cards from file
        with open(file_path, "r") as f:
            cards = json.load(f)

        if not isinstance(cards, list):
            raise CommandError("Invalid file format: expected a list of card objects")

        collection_id = get_collection_id(collection_name, HEADERS, options['url'])
        self.stdout.write(f"📦 Importing {len(cards)} cards to collection '{collection_name}' (ID {collection_id})")

        for i, card in enumerate(cards, 1):
            result = create_card(card, collection_id, HEADERS, options['force'], options['url'])
            if result.get('exists'):
                self.stdout.write(f"Skipped card [{i}/{len(cards)}], already exists: {card['name']} (ID {result['id']})")
                continue
            self.stdout.write(f"✅ [{i}/{len(cards)}] Created card: {result['name']} (ID {result['id']})")
        self.stdout.write(self.style.SUCCESS("All cards imported successfully!"))
