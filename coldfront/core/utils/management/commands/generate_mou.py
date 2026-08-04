"""A BRC-only management command for generating unsigned MOU PDFs for testing."""

import logging

from django.core.management.base import BaseCommand, CommandError

REQUEST_TYPE_TO_MODEL = {
    "new-project": "coldfront.core.project.models.SavioProjectAllocationRequest",
    "service-units-purchase": "coldfront.core.allocation.models.AllocationAdditionRequest",
    "secure-dir": "coldfront.core.allocation.models.SecureDirRequest",
}


class Command(BaseCommand):
    help = "Generate an unsigned MOU PDF for an existing request (BRC only)."
    logger = logging.getLogger("coldfront.commands")

    def add_arguments(self, parser):
        parser.add_argument(
            "--request-type",
            required=True,
            choices=list(REQUEST_TYPE_TO_MODEL),
            help="The type of request.",
        )
        parser.add_argument(
            "--pk",
            type=int,
            required=True,
            help="Primary key of the request object.",
        )
        parser.add_argument(
            "--output",
            required=True,
            help="Path to write the generated PDF.",
        )

    def handle(self, *args, **options):
        from coldfront.core.allocation.models import (
            AllocationAdditionRequest,
            SecureDirRequest,
        )
        from coldfront.core.project.models import SavioProjectAllocationRequest
        from coldfront.core.utils.mou import generate_unsigned_mou_pdf

        model_map = {
            "new-project": SavioProjectAllocationRequest,
            "service-units-purchase": AllocationAdditionRequest,
            "secure-dir": SecureDirRequest,
        }

        request_type = options["request_type"]
        pk = options["pk"]
        model_class = model_map[request_type]

        try:
            request_obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            raise CommandError(
                f"{model_class.__name__} with pk={pk} does not exist."
            ) from None

        pdf = generate_unsigned_mou_pdf(request_obj)
        if not pdf:
            raise CommandError(
                f"No MOU generator available for {request_type} pk={pk}. "
                f"Check that the request's allowance type supports MOU generation."
            )

        output_path = options["output"]
        with open(output_path, "wb") as f:
            f.write(pdf)

        self.logger.info("PDF written to %s.", output_path)
