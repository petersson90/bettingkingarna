from django.conf import settings
from django.db import models

# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=100)
    short = models.CharField(max_length=4)
    
    def __str__(self):
        return f'{self.name}'
    
    def number_of_wins(self):
        wins = 0
        for game in self.home_games.all():
            if game.home_goals > game.away_goals:
                wins += 1
        for game in self.away_games.all():
            if game.away_goals > game.home_goals:
                wins += 1
        return wins


class Game(models.Model):
    home_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='home_games')
    away_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='away_games')
    home_goals = models.PositiveSmallIntegerField(blank=True, null=True)
    away_goals = models.PositiveSmallIntegerField(blank=True, null=True)
    start_time = models.DateTimeField()
    
    def __str__(self):
        return f'{self.home_team} - {self.away_team}'
    
    def result(self):
        return f'{self.home_goals}-{self.away_goals}'
    
    def threeway(self):
        if self.home_goals > self.away_goals:
            return '1'
        elif self.home_goals == self.away_goals:
            return 'X'
        else:
            return '2'


class Bet(models.Model):
    game = models.ForeignKey(Game, on_delete=models.PROTECT, related_name='game_bets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    home_goals = models.PositiveSmallIntegerField()
    away_goals = models.PositiveSmallIntegerField()
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'game'], name='one_bet_per_user_per_game')
        ]
    
    def __str__(self):
        return f''
    
    def result(self):
        return f'{self.home_goals}-{self.away_goals}'
    
    def threeway(self):
        if self.home_goals > self.away_goals:
            return '1'
        elif self.home_goals == self.away_goals:
            return 'X'
        else:
            return '2'
    
    def points(self):
        points = 0
        if self.threeway() == self.game.threeway():
            points += 3
        if self.home_goals == self.game.home_goals:
            points += 1
        if self.away_goals == self.game.away_goals:
            points += 1
        if self.result() == self.game.result():
            points += 1
        return points
