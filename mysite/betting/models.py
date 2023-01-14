from django.db import models

# Create your models here.
class Game(models.Model):
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    start_time = models.DateTimeField()
