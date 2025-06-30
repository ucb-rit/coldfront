import requests
import io
import pypdf
import json
from django.core.management.base import BaseCommand

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
        first_year = int(year.split('-')[0])
        api_key = options['api_key']
        api = options['api']
        pdf_url = f'https://registrar.berkeley.edu/wp-content/uploads/UCB_AcademicCalendar_{year}.pdf'
        
        output_json_example = {
            'academic_year': f'{year}',
            'semesters': [
                {'name': 'Fall', 'start_date': f'{first_year}-08-25', 'end_date': f'{first_year}-12-15'},
                {'name': 'Spring', 'start_date': f'{first_year + 1}-01-10', 'end_date': f'{first_year + 1}-05-20'},
                {'name': 'Summer', 'start_date': f'{first_year + 1}-06-01', 'end_date': f'{first_year + 1}-08-15'}
            ]
        }

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
                f'Follow this JSON format:\n\n'
                f'{json.dumps(output_json_example, indent=2)}. We only care '
                f'about the semester names and dates. Do not include any other '
                f' information.'
            )
            
            parsed_data = response.output_text
        else:
            self.stdout.write(self.style.ERROR(
                'Unsupported API: {}'.format(api)))
            return

        try:
            parsed_json = json.loads(parsed_data)
            self.stdout.write(self.style.SUCCESS(
                'Parsed JSON: {}'.format(json.dumps(parsed_json, indent=2))))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(
                'Failed to parse JSON: {}'.format(e)))
                