from django.contrib.auth.models import User
from django.db import models

from simple_history.models import HistoricalRecords


class Department(models.Model):

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=5, unique=True)

    def __str__(self):
        return f'{self.name} ({self.code})'


class UserDepartment(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    is_authoritative = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.user.username}-{self.department.code}'

    class Meta:
        unique_together = ('user', 'department')
