import requests
import io
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
    help = 'Parse the UCB academic calendar and output JSON entries.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--calendar-year',
            required=True,
            help='The calendar year for the PDF to parse. e.g. "2025-26"'
        )
        parser.add_argument(
            '--api-key',
            required=True,
            help='API key '
        )
        parser.add_argument(
            '--api',
            required=False,
            default='openai',
            help='API to use for processing the calendar. Default is "openai".'
        )

    def handle(self, *args, **options):
        year = options['calendar_year']
        api_key = options['api_key']
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

        if api == 'openai':
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            response = client.responses.create(
                model='gpt-4',
                input='You can only output JSON. Please parse the following '
                f'UCB academic calendar text into JSON format:\n\n{text}\n\n'
                f'Follow this JSON format:\n\n {EXAMPLE_JSON}.\n\nWe only care'
                f'about the semester names and dates. Do not include any other '
                f'information.'
            )
            
            parsed_data = response.output_text
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
                