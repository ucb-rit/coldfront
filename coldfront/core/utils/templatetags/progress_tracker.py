from django import template

register = template.Library()

@register.inclusion_tag("progress_tracker.html")
def progress_tracker(steps):
    """
    Renders a DDS‐style progress tracker.

    `steps` should be a list of dicts:
      {
        "name":    str,       # step title
        "summary": str,       # subtitle / details
        "status":  str,       # one of "complete", "in-progress", "active", or ""
      }
    """
    # normalize aria‐current: true only for in-progress
    for step in steps:
        step["aria_current"] = "true" if step["status"] == "in-progress" else "false"
    return {"steps": steps}
