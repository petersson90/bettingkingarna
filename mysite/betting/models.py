from django.db import models

# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=100)
    short = models.CharField(max_length=4)
    
    def __str__(self):
        return f'{self.name}'


class Game(models.Model):
    home_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='home_games')
    away_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='away_games')
    start_time = models.DateTimeField()
    
    def __str__(self):
        return f'{self.home_team} - {self.away_team}'
