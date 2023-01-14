from django.db import models

from simple_history.models import HistoricalRecords

# Create your models here.
class Department(models.Model):
    name = models.CharField(max_length=128)  # The full name
    acronym = models.CharField(max_length=5)  # The five letter code

    def __str__(self):
        return f'{self.name} ({self.acronym})'

class UserDepartment(models.Model):
    user_profile = models.ForeignKey('user.UserProfile', on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    is_authoritative = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.user_profile.user.username}-{self.department.acronym}'

    class Meta:
        unique_together = ('user_profile', 'department')
