from django.utils import timezone
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Case, When

# Create your models here.
class Team(models.Model):
    ''' A team with related details '''
    name = models.CharField(max_length=100)

    class Meta:
        ordering = [Case(When(id=1, then=0), default=1), 'name']

    def __str__(self):
        return f'{self.name}'


class Competition(models.Model):
    ''' A competition with related details '''
    name = models.CharField(max_length=100)
    # start_date = models.DateField()
    # end_date = models.DateField()
    season = models.CharField(max_length=5)
    teams = models.ManyToManyField(Team, related_name='competitions')

    def __str__(self):
        return f'{self.name} {self.season}'


class Game(models.Model):
    ''' A game with related details '''
    competition = models.ForeignKey(Competition, on_delete=models.PROTECT, related_name="games")
    home_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='home_games')
    away_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='away_games')
    start_time = models.DateTimeField(help_text='Format: 2023-05-01 19:00:00')
    # location = models.CharField(max_length=200)
    home_goals = models.PositiveSmallIntegerField(default=0)
    away_goals = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f'{self.home_team} - {self.away_team}'

    def has_started(self):
        ''' True if the start time of the game is in the past '''
        return self.start_time < timezone.now()

    def result(self):
        ''' Returns the game result displayed as home_goals-away_goals'''
        if self.home_goals is None or self.away_goals is None:
            return None
        return f'{self.home_goals}-{self.away_goals}'

    def threeway(self):
        ''' Returns the game result as 1 (home win), X (draw) or 2 (away win)'''
        if self.home_goals is None or self.away_goals is None:
            return None
        if self.home_goals > self.away_goals:
            return '1'
        elif self.home_goals == self.away_goals:
            return 'X'
        else:
            return '2'


class Bet(models.Model):
    ''' A bet for a specific game and user '''
    game = models.ForeignKey(Game, on_delete=models.PROTECT, related_name='bets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    home_goals = models.PositiveSmallIntegerField(default=0)
    away_goals = models.PositiveSmallIntegerField(default=0)
    points = models.PositiveSmallIntegerField(default=0)
    # Hidden fields to keep track of creation and update time
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'game'], name='one_bet_per_user_per_game')
        ]

    def __str__(self):
        return f'{self.game}: {self.result()}'

    def is_updated(self):
        ''' Returns true if the bet has been updated '''
        return self.updated - self.created > timezone.timedelta(seconds=1)

    def result(self):
        ''' Returns the result in the bet '''
        return f'{self.home_goals}-{self.away_goals}'

    def threeway(self):
        ''' Returns the bet result as 1 (home win), X (draw) or 2 (away win) '''
        if self.home_goals > self.away_goals:
            return '1'
        elif self.home_goals == self.away_goals:
            return 'X'
        else:
            return '2'

    def calculate_points(self):
        ''' Calculates the points for each bet '''
        if not self.game.has_started():
            return 0
        points = 0
        if self.threeway() == self.game.threeway():
            points += 3
            if self.threeway() == 'X' and self.home_goals != self.game.home_goals:
                points += 1
        if self.home_goals == self.game.home_goals:
            points += 1
        if self.away_goals == self.game.away_goals:
            points += 1
        if self.result() == self.game.result():
            points += 1
        return points

    def save(self, *args, game_updated=False, **kwargs):
        ''' Update of the save method to restrict saving after the game has started '''
        if self.game.start_time <= timezone.now() and not game_updated:
            raise ValueError("Cannot save bet for a game that has already started.")
        if not game_updated:
            self.updated = timezone.now()
        self.points = self.calculate_points()
        super().save(*args, **kwargs)


@receiver(post_save, sender=Game)
def update_bet_points(sender, instance, **kwargs):
    for bet in instance.bets.all():
        bet.save(game_updated=True)


class StandingPrediction(models.Model):
    ''' A bet for the final standings of a specific competition '''
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    competition = models.ForeignKey(Competition, on_delete=models.PROTECT)
    standing = models.CharField(max_length=100)
    top_scorer = models.CharField(max_length=100)
    most_assists = models.CharField(max_length=100)
    # Hidden fields to keep track of creation and update time
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'competition'], name='one_bet_per_user_per_competition')
        ]

    def calculate_points(self, actual_standing: list[Team]):
        ''' Returns the points for the standings bet '''
        points = 0
        predicted_standing = [Team.objects.get(team_id) for team_id in self.standing.split(',')]
        for position, team in enumerate(predicted_standing):
            diff = position - actual_standing.index(team)
            points -= abs(diff)
        return points
