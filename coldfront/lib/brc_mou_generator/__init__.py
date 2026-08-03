import abc
import base64
import datetime
import importlib.resources

import jinja2
from playwright.sync_api import sync_playwright

templates_dir = str(importlib.resources.files(__name__) / "templates")
template_loader = jinja2.FileSystemLoader(searchpath=templates_dir)
template_env = jinja2.Environment(loader=template_loader)

# Embed the logo as a base64 data URI at import time so Playwright's
# set_content() can resolve it without needing a file:// base URL.
with (
    importlib.resources.files(__name__).joinpath("static/brc_logo.png").open("rb") as _f
):
    _brc_logo_b64 = f"data:image/png;base64,{base64.b64encode(_f.read()).decode()}"


class MouGenerator(abc.ABC):
    """Abstract base for MOU PDF generators.

    Subclasses declare ``_template_name`` and implement ``_build_context``.
    ``generate()`` is the template method: it assembles the common context,
    delegates type-specific context to the subclass, then renders the PDF.
    """

    _template_name: str

    def __init__(self, director_name, director_title, director_signature_b64):
        self._director_name = director_name
        self._director_title = director_title
        self._director_signature_b64 = director_signature_b64

    def generate(self, first_name, last_name, project_name, **kwargs) -> bytes:
        context = self._common_context(first_name, last_name, project_name)
        self._build_context(context, **kwargs)
        return self._render(context)

    @abc.abstractmethod
    def _build_context(self, context: dict, **kwargs) -> None:
        """Populate ``context`` with type-specific template variables."""

    def _common_context(self, first_name, last_name, project_name) -> dict:
        return {
            "brc_logo_b64": _brc_logo_b64,
            "director_name": self._director_name,
            "director_title": self._director_title,
            "director_signature_b64": f"data:image/png;base64,{self._director_signature_b64}",
            "pi_name": f"{first_name} {last_name}",
            "date": datetime.date.today().strftime("%B %d, %Y"),
            "project": project_name,
        }

    def _render(self, context: dict) -> bytes:
        html = template_env.get_template(self._template_name).render(context)
        with sync_playwright() as p:
            with p.chromium.launch(
                args=[
                    "--no-sandbox",  # required in Docker / restricted-namespace VMs
                    "--disable-dev-shm-usage",  # avoids /dev/shm OOM in containers
                ]
            ) as browser:
                page = browser.new_page()
                page.set_content(html, wait_until="networkidle")
                pdf = page.pdf(
                    format="Letter",
                    print_background=True,
                    scale=0.82,
                    margin={
                        "top": "0.4in",
                        "right": "0.4in",
                        "bottom": "0.4in",
                        "left": "0.4in",
                    },
                )
        return pdf


class InstructionalMouGenerator(MouGenerator):
    _template_name = "instructional.html"

    def _build_context(self, context, service_units, extra_fields, allowance_end):
        context["service_units"] = service_units
        context["course_dept"] = extra_fields["course_department"]
        context["dept_and_pi"] = f"{context['course_dept']}/{context['pi_name']}"
        context["between"] = f"{self._director_name} (BRC) and {context['pi_name']}"
        context["re"] = f"{context['dept_and_pi']} ICA Agreement"
        context["course_name"] = extra_fields["course_name"]
        context["point_of_contact"] = extra_fields["point_of_contact"]
        context["num_students"] = int(extra_fields["num_students"])
        context["allowance_last_month"] = allowance_end.strftime("%B %Y")
        context["signature"] = f"{context['pi_name']}<br>{context['course_dept']}"


class RechargeMouGenerator(MouGenerator):
    _template_name = "recharge.html"

    def _build_context(self, context, service_units, extra_fields):
        context["service_units"] = service_units
        context["between"] = f"{self._director_name} (BRC) and {context['pi_name']}"
        context["re"] = f"{context['project']} Savio Allowance Purchase Agreement"
        context["chartstring"] = extra_fields["campus_chartstring"]
        context["cost"] = f"${(0.01 * service_units):.2f} ($0.01/SU)"
        context["signature"] = f"{context['pi_name']}<br>{context['project']}"


class SecureDirMouGenerator(MouGenerator):
    _template_name = "secure_dir.html"

    def _build_context(self, context, department):
        context["between"] = f"RTL / Research IT and {department}/{context['pi_name']}"
        context["re"] = "P2/P3 Savio project Researcher Use Agreement"
        context["signature"] = f"{context['pi_name']}<br>{context['project']}"
