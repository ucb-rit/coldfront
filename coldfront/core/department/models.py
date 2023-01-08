from django.db import models

from simple_history.models import HistoricalRecords

# Create your models here.
class Department(models.Model):
    name = models.CharField(max_length=128)  # The full name
    acronym = models.CharField(max_length=5)  # The five letter code

    def __str__(self):
        return f'{self.name} ({self.acronym})'
