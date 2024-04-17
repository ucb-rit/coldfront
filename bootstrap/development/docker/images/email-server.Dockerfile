ARG BASE_IMAGE_TAG=latest
FROM coldfront-app-base:${BASE_IMAGE_TAG}

CMD ["python3", "-m", "smtpd", "-d", "-n", "-c", "DebuggingServer", "0.0.0.0:1025"]
