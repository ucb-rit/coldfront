ARG BASE_IMAGE_TAG=latest
FROM coldfront-app-base:${BASE_IMAGE_TAG}

CMD ["python3", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "manage.py", "runserver", "0.0.0.0:80"]
