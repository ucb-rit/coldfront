from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.utils_.renewal_utils import get_renewal_survey
from coldfront.core.project.utils_.renewal_utils import get_gspread_wks
from coldfront.core.project.utils_.renewal_utils import renewal_survey_answer_conversion

from coldfront.core.utils.common import add_argparse_dry_run_argument

import logging
import time

class Command(BaseCommand):
    help = 'Export existing responses to the on-site renewal survey to Google '\
            'Form'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        """ This command exports the existing responses to the on-site renewal 
        survey to Google Sheets. Because of usage limits on Google API, only 2 
        responses can be exported to the Sheet at a time, so a 30 second 
        timeout is set before each response is written. As there are around 200 
        existing responses, this command will take around 2 hours to 
        complete. """
        
        allocation_period = AllocationPeriod.objects.get(
            name="Allowance Year 2024 - 2025")
        requests = AllocationRenewalRequest.objects.filter(
            allocation_period=allocation_period)
        survey_answers = [i for i in requests if 
                            i.renewal_survey_answers != {}]
        
        survey_data = get_renewal_survey(allocation_period.name)
        wks = get_gspread_wks(survey_data["sheet_id"], 0)

        survey_questions = [
            'timestamp',
            'which_brc_services_used',
            'publications_supported_by_brc',
            'grants_supported_by_brc',
            'recruitment_or_retention_cases',
            'classes_being_taught',
            'brc_recommendation_rating',
            'brc_recommendation_rating_reason',
            'how_brc_helped_bootstrap_computational_methods',
            'how_important_to_research_is_brc',
            'do_you_use_mybrc',
            'mybrc_comments',
            'which_open_ondemand_apps_used',
            'brc_feedback',
            'colleague_suggestions',
            'indicate_topic_interests',
            'training_session_usefulness_of_computational_platforms_training',
            'training_session_usefulness_of_basic_savio_cluster',
            'training_session_usefulness_of_advanced_savio_cluster',
            'training_session_usefulness_of_singularity_on_savio',
            'training_session_usefulness_of_analytic_envs_on_demand',
            'training_session_other_topics_of_interest',
            'allocation_period',
            'pi_name',
            'pi_username',
            'project_name',
            'requester_name',
            'requester_username'
        ]

        row_coor = len(wks.col_values(1)) + 1
        for i in range(len(survey_answers)):
            all_answers = survey_answers[i]
            print(f'Adding {all_answers.requester.username}\'s answers...')

            # Because of usage limits, we can only write in around 2 responses
            # per minute.
            time.sleep(30)

            col_coor = 1
            for question in survey_questions:
                answer = renewal_survey_answer_conversion(question, all_answers)
                wks.update_cell(row_coor, col_coor, answer)
                col_coor += 1
            row_coor += 1
        
        print('Finished!')
    
