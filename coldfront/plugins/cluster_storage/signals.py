import logging

from django.dispatch import receiver

from coldfront.core.project.utils_.new_project_user_utils import project_user_activated
from coldfront.plugins.cluster_storage.services.directory_service import DirectoryService


logger = logging.getLogger(__name__)


@receiver(project_user_activated)
def add_project_user_to_faculty_storage_allocation(sender, **kwargs):
    """When a ProjectUser is activated, add the user to the project's
    Faculty Storage Allocation, if it has one.

    Parameters:
        - sender: The class that sent the signal
        - **kwargs:
            - project_user: The ProjectUser object
    """
    project_user = kwargs.get('project_user')
    project = project_user.project
    user = project_user.user

    if not project or not user:
        logger.warning(
            'project_user_activated signal received without project or user')
        return

    try:
        # Get a DirectoryService for the project's existing allocation
        directory_service = DirectoryService.for_project(project)

        if directory_service:
            # Add the user to the allocation
            directory_service.add_user_to_directory(user)
            logger.info(
                f'Added User {user.username} to faculty storage allocation '
                f'for Project {project.name}')
        else:
            logger.debug(
                f'Project {project.name} does not have a faculty storage '
                f'allocation, skipping user addition')

    except Exception as e:
        # Log but don't raise - we don't want to break the user addition flow
        logger.exception(
            f'Error adding User {user.username} to faculty storage '
            f'allocation for Project {project.name}: {e}')
