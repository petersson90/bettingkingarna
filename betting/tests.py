from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Bet, Team, Competition, Game
from django.utils import timezone
import unittest.mock as mock

# Create your tests here.

class BetModelTest(TestCase):
    def setUp(self):
        # Create some related objects for testing
        self.user = get_user_model().objects.create_user(
            username = 'testuser',
            password = 'testpassword',
        )
        self.team1 = Team.objects.create(name='Team A')
        self.team2 = Team.objects.create(name='Team B')
        self.competition = Competition.objects.create(name='Test Competition', season='2023')
        self.game1 = Game.objects.create(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() + timezone.timedelta(hours=1),
        )
        self.game2 = Game.objects.create(
            competition=self.competition,
            home_team=self.team2,
            away_team=self.team1,
            start_time=timezone.now() + timezone.timedelta(hours=2),
        )

    def test_is_updated_for_new_bet(self):
        # Simulate an unchanged bet by not making any changes
        unchanged_bet = Bet.objects.create(
            game=self.game1,
            user=self.user,
            home_goals=2,
            away_goals=0,
        )

        print(unchanged_bet.created, unchanged_bet.updated, unchanged_bet.is_updated())

        # An unchanged bet should not be considered updated
        self.assertFalse(unchanged_bet.is_updated())

    def test_is_updated_for_changed_bet(self):
        creation_time = timezone.now() - timezone.timedelta(days=1)

        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = creation_time

            # Create a Bet instance
            bet = Bet.objects.create(
                game=self.game2,
                user=self.user,
                home_goals=1,
                away_goals=2,
            )

        print(bet.created, bet.updated, bet.is_updated())
        # Initially, the bet should not be considered updated
        self.assertFalse(bet.is_updated())



        # Update the bet's goals
        bet.home_goals = 3
        bet.away_goals = 2
        bet.save()

        print(bet.created, bet.updated, bet.is_updated())
        # After updating, the bet should be considered updated
        self.assertTrue(bet.is_updated())
