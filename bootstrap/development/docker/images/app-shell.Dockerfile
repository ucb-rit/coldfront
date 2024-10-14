ARG BASE_IMAGE_TAG=latest
FROM coldfront-app-base:${BASE_IMAGE_TAG}

CMD ["sleep", "infinity"]
