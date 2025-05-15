from coldfront.core.project.models import ProjectUserJoinRequest, ProjectUserStatusChoice
from coldfront.core.allocation.utils import has_cluster_access

def project_join_progress(user):
    """
    Build a 5‑step timeline for a user's *most recent* join‑project request.

    Steps:
      1. Request Sent
      2. PI Approved
      3. Cluster Request Generated
      4. Admin Processing
      5. Access Granted
    """
    # 1) grab their latest join request
    join_req = (
        ProjectUserJoinRequest.objects
        .filter(project_user__user=user)
        .order_by('-created')
        .first()
    )
    if not join_req:
        return []

    pu = join_req.project_user
    # has PI approved? (we consider anything *but* 'Pending - Add' as approved)
    pi_approved = (pu.status.name != 'Pending - Add')
    # has the cluster admins finished granting access?
    access_granted = has_cluster_access(user)

    # decide which step is currently "in‑progress":
    #  — if PI hasn’t yet approved: step index 1
    #  — elif approved but no access yet: step index 3
    #  — elif access_granted: no in‑progress (all complete)
    if not pi_approved:
        current = 1
    elif not access_granted:
        current = 3
    else:
        current = None

    raw_steps = [
        {
            "name":    "Request Sent",
            "summary": f"Requested on {join_req.created.date()}",
        },
        {
            "name":    "PI Approved",
            "summary": "PI has approved your request",
        },
        {
            "name":    "Cluster Request Generated",
            "summary": "Cluster access queued for admins",
        },
        {
            "name":    "Admin Processing",
            "summary": "Waiting on cluster administrators",
        },
        {
            "name":    "Access Granted",
            "summary": "You now have cluster access",
        },
    ]

    steps = []
    for idx, step in enumerate(raw_steps):
        # default status
        if access_granted:
            status = "complete"
        else:
            if current is None:
                status = ""
            elif idx < current:
                status = "complete"
            elif idx == current:
                status = "in-progress"
            elif idx == current + 1:
                status = "active"
            else:
                status = ""
        steps.append({
            "name":        step["name"],
            "summary":     step["summary"],
            "status":      status,
        })
    return steps
