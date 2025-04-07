from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Case, When, Sum, Window, F, IntegerField, ExpressionWrapper, Min
from django.db.models.functions import Rank, Abs
from django.urls import reverse

import math

# Create your models here.
class Team(models.Model):
    ''' A team with related details '''
    name = models.CharField(max_length=100)
    logo = models.FileField(null=True, blank=True, upload_to='team_logos/')

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
    excluded = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.name} {self.season}'


class Game(models.Model):
    ''' A game with related details '''
    competition = models.ForeignKey(Competition, on_delete=models.PROTECT, related_name='games')
    home_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='home_games')
    away_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='away_games')
    start_time = models.DateTimeField(help_text='Format: 2023-05-01 19:00:00')
    # location = models.CharField(max_length=200)
    home_goals = models.PositiveSmallIntegerField(default=0)
    away_goals = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f'{self.home_team} - {self.away_team}'

    def get_absolute_url(self):
        ''' Return the url of the game detail page '''
        return reverse("betting:detail", kwargs={"game_id": self.pk})

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

    def get_leaderboard(self):
        """Return the leaderboard at the start of this game."""
        leaderboard = (
            Bet.objects.filter(
                game__start_time__year=self.start_time.year,
                game__start_time__lt=self.start_time
            )
            .values('user')
            .annotate(
                game_points=Sum('points'),
                goal_difference=Sum(
                    ExpressionWrapper(
                        Case(
                            When(game__home_team__id = 1, then=(F('game__away_goals') - F('game__home_goals')) - (F('away_goals') - F('home_goals'))),
                            default=(F('game__home_goals') - F('game__away_goals')) - (F('home_goals') - F('away_goals'))
                        ),
                        output_field=IntegerField()
                    )
                ),
                goals_scored=Sum(
                    ExpressionWrapper(
                        Case(
                            When(game__home_team__id = 1, then=F('home_goals') - F('game__home_goals')),
                            default=F('away_goals') - F('game__away_goals')
                        ),
                        output_field=IntegerField()
                    )
                ),
                position=Window(
                    expression=Rank(),
                    order_by=[
                        F('game_points').desc(),
                        Abs(F('goal_difference')).asc(),
                        Abs(F('goals_scored')).asc()
                    ]
                )
            )
        )

        User = get_user_model()
        users = {user.id: user for user in User.objects.all()}

        competition = Competition.objects.get(pk=self.competition.id)
        standings = Standing.objects.filter(competition=competition).prefetch_related('team_positions').latest('round')
        sort_order_list = list(standings.team_positions.values_list('team_id', flat=True).order_by('position'))
        competition_standings = sorted(competition.teams.all(), key=lambda team: sort_order_list.index(team.id))
        top_scorer_list = standings.top_scorer
        most_assists_list = standings.most_assists

        try:
            user_standing_predictions = StandingPrediction.objects.select_related('user').prefetch_related('team_positions__team').filter(competition=competition)
            table_points = {}            
            for user_standing_prediction in user_standing_predictions:
                user = user_standing_prediction.user
                teams = [(standing_prediction_team.position, standing_prediction_team.team) for standing_prediction_team in user_standing_prediction.team_positions.all()]
                user_top_scorer = user_standing_prediction.top_scorer
                user_most_assists = user_standing_prediction.most_assists
                    
                bet_points = []
                for position, team in teams:
                    diff = position - competition_standings.index(team) - 1
                    bet_points.append(-abs(diff))
                user_table_points = sum(bet_points)

                extra_bet = 0

                if user_top_scorer in top_scorer_list:
                    extra_bet += 6
                if user_most_assists in most_assists_list:
                    extra_bet += 6
                
                table_points[user] = {
                    'points': user_table_points,
                    'extra_bet': extra_bet
                }

        except StandingPrediction.DoesNotExist:
            user_top_scorer = 'N/A'
            user_most_assists = 'N/A'

        
        for row in leaderboard:
            row['user'] = users.get(row['user'])
            row['table_points'] = table_points.get(row['user'], {}).get('points', 0)
            row['extra_bet'] = table_points.get(row['user'], {}).get('extra_bet', 0)
            row['total_score'] = row.get('game_points', 0) + row.get('table_points', 0) + row.get('extra_bet', 0)

        leaderboard = sorted(
            leaderboard,
            key=lambda x: (
                -x['total_score'],
                abs(x['goal_difference']),
                abs(x['goals_scored'])
            )
        )

        for position, entry in enumerate(leaderboard, 1):
            entry['position'] = position

        return leaderboard

    def get_deadlines(self):
        """Return the deadlines for all users in this game."""
        leaderboard = self.get_leaderboard()

        user_deadlines = {
            entry['user']: self.start_time - timezone.timedelta(minutes=60 - math.ceil(entry['position'] / 2) * 10)
            for entry in leaderboard
        }

        return user_deadlines

    def get_deadline(self, user):
        """Dynamically calculates the submission deadline for this user in this game."""
        if not user.is_authenticated:
            return None  # No deadline for anonymous users

        deadlines = self.get_deadlines()

        return deadlines.get(user.id, None)


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
            models.UniqueConstraint(
                fields=['user', 'game'],
                name='one_bet_per_user_per_game'
            )
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

    def can_submit(self):
        """Check if the user can still submit or modify this bet."""
        deadline = self.game.get_deadlines().get(self.user, self.game.start_time)
        return timezone.now() <= deadline

    def save(self, *args, game_updated=False, **kwargs):
        ''' Update of the save method to restrict saving after the game has started '''
        if self.game.start_time <= timezone.now() and not game_updated:
            raise ValidationError('Cannot save bet for a game that has already started.')
        if not self.can_submit() and not game_updated:
            raise ValidationError('Cannot save bet after your deadline.')
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
    standing = models.CharField(max_length=100, blank=True)
    top_scorer = models.CharField(max_length=100, blank=True)
    most_assists = models.CharField(max_length=100, blank=True)
    # Hidden fields to keep track of creation and update time
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'competition'],
                name='one_bet_per_user_per_competition'
            )
        ]

    def calculate_points(self, standing, TOP_BOTTOM=4, POINTS_CORRECT=6, POINTS_ALMOST=2):
        ''' Returns the points for the standings bet '''
        points = 0
        standing = [(team_position.position, team_position.team) for team_position in standing.team_positions.all().prefetch_related("team").order_by('position')]

        if self.competition == 3:
            predicted_standing = [Team.objects.get(team_id) for team_id in self.standing.split(',')]
            for position, team in enumerate(predicted_standing):
                diff = position - standing.index(team)
                points -= abs(diff)
            return points

        top_teams = standing[:TOP_BOTTOM]
        bottom_teams = standing[-TOP_BOTTOM:]

        predicted_standing = [(prediction.position, prediction.team) for prediction in self.team_positions.all().prefetch_related("team").order_by('position')]
        predicted_top_teams = predicted_standing[:TOP_BOTTOM]
        predicted_bottom_teams = predicted_standing[-TOP_BOTTOM:]

        for position, team in predicted_top_teams:
            if (position, team) in top_teams:
                points += POINTS_CORRECT
            elif team in [tup[1] for tup in top_teams]:
                points += POINTS_ALMOST

        for position, team in predicted_bottom_teams:
            if (position, team) in bottom_teams:
                points += POINTS_CORRECT
            elif team in [tup[1] for tup in bottom_teams]:
                points += POINTS_ALMOST

        return points


class StandingPredictionTeam(models.Model):
    ''' Enables a list of teams to be connected to a StandingPrediction '''
    standing_prediction = models.ForeignKey(StandingPrediction, on_delete=models.PROTECT, related_name='team_positions')
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    position = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['standing_prediction', 'position'],
                name='unique_position_per_prediction'
            ),
            models.UniqueConstraint(
                fields=['standing_prediction', 'team'],
                name='unique_team_per_prediction'
            )
        ]

    def clean(self):
        super().clean()

        # Check if the selected team belongs to any of the related competitions of the prediction
        if not self.team.competitions.filter(id=self.standing_prediction.competition.id).exists():
            raise ValidationError(f'{self.team} does not belong to this competition')

        max_position = self.standing_prediction.competition.teams.count()
        if self.position < 1 or self.position > max_position:
            raise ValidationError(f'Position must be between 1 and {max_position}')

    def save(self, *args, **kwargs):
        self.clean()  # Validate the team and position before saving
        super(StandingPredictionTeam, self).save(*args, **kwargs)

class Standing(models.Model):
    ''' A record of the standings of a specific competition at a point in time '''
    competition = models.ForeignKey(Competition, on_delete=models.PROTECT)
    round = models.PositiveSmallIntegerField()
    top_scorer = models.CharField(max_length=100, blank=True)
    most_assists = models.CharField(max_length=100, blank=True)
    # Hidden fields to keep track of creation and update time
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['competition', 'round'],
                name='one_standing_per_round_per_competition'
            )
        ]


class TeamPosition(models.Model):
    ''' Enables a position/team relationship to be connected to a specific Standing record '''
    standing = models.ForeignKey(Standing, on_delete=models.PROTECT, related_name='team_positions')
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    position = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['standing', 'position'],
                name='unique_position_per_standing'
            ),
            models.UniqueConstraint(
                fields=['standing', 'team'],
                name='unique_team_per_standing'
            )
        ]

    def clean(self):
        super().clean()

        # Check if the selected team belongs to any of the related competitions of the prediction
        if not self.team.competitions.filter(id=self.standing.competition.id).exists():
            raise ValidationError(f'{self.team} does not belong to this competition')

        max_position = self.standing.competition.teams.count()
        if self.position < 1 or self.position > max_position:
            raise ValidationError(f'Position must be between 1 and {max_position}')

    def save(self, *args, **kwargs):
        self.clean()  # Validate the team and position before saving
        super(TeamPosition, self).save(*args, **kwargs)
