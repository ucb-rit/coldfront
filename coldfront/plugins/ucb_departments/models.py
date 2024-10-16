from django.db import models

from simple_history.models import HistoricalRecords

# Create your models here.
class Department(models.Model):
    name = models.CharField(max_length=128)  # The full name
    code = models.CharField(max_length=5, unique=True)  # The five letter code

    def __str__(self):
        return f'{self.name} ({self.code})'

class UserDepartment(models.Model):
    # TODO: Evaluate whether this comment is still true, given that `through` is
    #  no longer in use.
    # This field must be named 'userprofile' because django-simple-history uses
    # the lowercase name of the UserProfile model to filter UserDepartments.
    # https://github.com/jazzband/django-simple-history/blob/9efbfabd47c8d9ce7dae44b9ffa1b088b6121aed/simple_history/models.py#L671
    userprofile = models.ForeignKey('user.UserProfile', on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    is_authoritative = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.userprofile.user.username}-{self.department.code}'

    class Meta:
        unique_together = ('userprofile', 'department')
