import requests
import io
import os
import pypdf
import json
from django.core.management.base import BaseCommand


EXAMPLE_JSON ='''[
    {
        "name": "Fall Semester 2025",
        "start_date": "2025-08-20",
        "end_date": "2025-12-19"
    },
    {
        "name": "Spring Semester 2026",
        "start_date": "2026-01-13",
        "end_date": "2026-05-15"
    },
    {
        "name": "Summer Sessions 2026 - Session A",
        "start_date": "2026-05-26",
        "end_date": "2026-07-02"
    },
    {
        "name": "Summer Sessions 2026 - Session B",
        "start_date": "2026-06-08",
        "end_date": "2026-08-14"
    },
    {
        "name": "Summer Sessions 2026 - Session C",
        "start_date": "2026-06-22",
        "end_date": "2026-08-14"
    },
    {
        "name": "Summer Sessions 2026 - Session D",
        "start_date": "2026-07-06",
        "end_date": "2026-08-14"
    },
    {
        "name": "Summer Sessions 2026 - Session E",
        "start_date": "2026-07-27",
        "end_date": "2026-08-14"
    },
    {
        "name": "Summer Sessions 2026 - Session F",
        "start_date": "2026-07-06",
        "end_date": "2026-07-24"
    }
]'''


class Command(BaseCommand):
    help = (
        'Parse the UCB academic calendar and output JSON entries. Note: To use '
        'this command, you must install openai and pypdf via Pip.')
    # TODO: Once Python has been upgraded, these may be re-included in
    #  requirements.txt.

    def add_arguments(self, parser):
        parser.add_argument(
            '--calendar-year',
            required=True,
            help='The calendar year for the PDF to parse. e.g. "2025-26"'
        )
        parser.add_argument(
            '--api',
            required=False,
            default='openai',
            help='API to use for processing the calendar. Default is "openai".'
        )

    def handle(self, *args, **options):
        year = options['calendar_year']
        api = options['api']
        pdf_url = f'https://registrar.berkeley.edu/wp-content/uploads/UCB_AcademicCalendar_{year}.pdf'

        # Fetch the PDF
        response = requests.get(pdf_url)
        if response.status_code != 200:
            self.stdout.write(
                self.style.ERROR('Failed to fetch PDF at {}'.format(pdf_url)))
            return
        io_bytes = io.BytesIO(response.content)

        # Read the PDF
        pdf_reader = pypdf.PdfReader(io_bytes)
        text = ''
        for page in pdf_reader.pages:
            text += page.extract_text()
        parsed_data = ''

        prompt = (
            f'You can only output JSON. Please parse the following UCB '
            f'academic calendar text into JSON format:\n\n{text}\n\nFollow '
            f'this JSON format:\n\n {EXAMPLE_JSON}.\n\nWe only care about the '
            f'semester names and dates. Do not include any other information.')

        if api == 'openai':
            from openai import OpenAI

            client_kwargs = {}

            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                self.stdout.write(
                    self.style.ERROR(
                        'Please set the OPENAI_API_KEY environment variable.'))
                return
            client_kwargs['api_key'] = api_key

            api_url = os.environ.get('OPENAI_API_BASE_URL')
            if not api_url:
                self.stdout.write(
                    self.style.WARNING(
                        'No OPENAI_API_BASE_URL set. Using default.'))
            else:
                client_kwargs['base_url'] = api_url

            model = os.environ.get('OPENAI_MODEL')
            if not model:
                model = 'openai/gpt-4o'
                self.stdout.write(
                    self.style.WARNING(
                        f'No OPENAI_MODEL set. Using default: {model}.'))

            client = OpenAI(**client_kwargs)

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                    },
                ]
            )

            parsed_data = response.choices[-1].message.content.strip()

            # Remove markdown code blocks if present.
            if parsed_data.startswith('```json'):
                parsed_data = parsed_data[7:]  # Remove ```json
            elif parsed_data.startswith('```'):
                parsed_data = parsed_data[3:]   # Remove ```
            if parsed_data.endswith('```'):
                parsed_data = parsed_data[:-3]  # Remove closing ```

            parsed_data = parsed_data.strip()
        else:
            self.stdout.write(self.style.ERROR(
                'Unsupported API: {}'.format(api)))
            return

        try:
            parsed_json = json.loads(parsed_data)
            self.stdout.write(self.style.SUCCESS(
                json.dumps(parsed_json, indent=2)))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(
                'Failed to parse JSON: {}'.format(e)))
