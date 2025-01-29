import os
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Bet, Team, Competition, Game, StandingPrediction
from django.utils import timezone
import unittest.mock as mock

# Create your tests here.
class TeamModelTest(TestCase):
    def tearDown(self):
        # Clean up any files created during the tests
        teams = Team.objects.all()
        for team in teams:
            if team.logo:
                if os.path.isfile(team.logo.path):
                    os.remove(team.logo.path)

    def test_team_string_representation(self):
        team = Team.objects.create(name='Manchester United')
        self.assertEqual(str(team), 'Manchester United')

    def test_team_with_logo(self):
        logo = SimpleUploadedFile('test_logo.svg', b'file_content', content_type='image/svg+xml')
        team = Team.objects.create(name='Chelsea', logo=logo)
        self.assertIsNotNone(team.id)
        self.assertEqual(team.name, 'Chelsea')
        self.assertIsNotNone(team.logo)
        self.assertEqual(team.logo.name, 'team_logos/test_logo.svg')


class CompetitionModelTest(TestCase):
    def setUp(self):
        self.team1 = Team.objects.create(name="Manchester United")
        self.team2 = Team.objects.create(name="Arsenal")
        self.team3 = Team.objects.create(name="Chelsea")

    def test_competition_string_representation(self):
        competition = Competition.objects.create(name="Premier League", season="23/24")
        self.assertEqual(str(competition), "Premier League 23/24")
    
    def test_competition_cannot_have_duplicate_teams(self):
        competition = Competition.objects.create(name="Premier League", season="23/24")
        self.assertEqual(competition.teams.count(), 0)
        competition.teams.add(self.team1, self.team1)
        self.assertEqual(competition.teams.count(), 1)


class GameModelTest(TestCase):
    def setUp(self):
        self.team1 = Team.objects.create(name="Manchester United")
        self.team2 = Team.objects.create(name="Arsenal")
        self.competition = Competition.objects.create(name="Premier League", season="23/24")

    def test_game_string_representation(self):
        game = Game.objects.create(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() + timezone.timedelta(hours=1),
        )
        self.assertEqual(str(game), "Manchester United - Arsenal")

    def test_game_home_goals_cannot_be_negative(self):
        game = Game(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now(),
            home_goals=-1,
            away_goals=0,
        )
        with self.assertRaises(ValidationError):
            game.full_clean()

    def test_game_away_goals_cannot_be_negative(self):
        game = Game(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now(),
            home_goals=0,
            away_goals=-1,
        )
        with self.assertRaises(ValidationError):
            game.full_clean()

    def test_game_has_not_started(self):
        game = Game.objects.create(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() + timezone.timedelta(hours=1),
        )
        self.assertFalse(game.has_started())

    def test_game_has_started(self):
        game = Game.objects.create(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() - timezone.timedelta(hours=1),
        )
        self.assertTrue(game.has_started())
    
    def test_game_result(self):
        game = Game.objects.create(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() - timezone.timedelta(hours=1),
        )
        self.assertEqual(game.result(), '0-0')
        game.home_goals = 1
        game.save()
        self.assertEqual(game.result(), '1-0')
        game.away_goals = 1
        game.save()
        self.assertEqual(game.result(), '1-1')
        game.away_goals = 2
        game.save()
        self.assertEqual(game.result(), '1-2')

    def test_game_threeway_home_win(self):
        game = Game(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() - timezone.timedelta(hours=1),
            home_goals=1,
            away_goals=0,
        )
        self.assertEqual(game.threeway(), '1')
        
    def test_game_threeway_draw(self):
        game = Game(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() - timezone.timedelta(hours=1),
            home_goals=1,
            away_goals=1,
        )
        self.assertEqual(game.threeway(), 'X')

    def test_game_threeway_away_win(self):
        game = Game(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() - timezone.timedelta(hours=1),
            home_goals=1,
            away_goals=2,
        )
        self.assertEqual(game.threeway(), '2')

class BetModelTest(TestCase):
    def setUp(self):
        # Create some related objects for testing
        self.user = get_user_model().objects.create_user(
            username = 'testuser',
            password = 'testpassword',
        )
        self.team1 = Team.objects.create(name='Manchester United')
        self.team2 = Team.objects.create(name='Arsenal')
        self.competition = Competition.objects.create(name='Premier League', season='23/24')
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

    def test_bet_home_goals_cannot_be_negative(self):
        bet = Bet(
            game=self.game1,
            user=self.user,
            home_goals=-1,
        )
        with self.assertRaises(ValidationError):
            bet.full_clean()

    def test_bet_away_goals_cannot_be_negative(self):
        bet = Bet(
            game=self.game1,
            user=self.user,
            away_goals=-1,
        )
        with self.assertRaises(ValidationError):
            bet.full_clean()

    def test_bet_is_updated_for_unchanged_bet(self):
        unchanged_bet = Bet.objects.create(
            game=self.game1,
            user=self.user,
            home_goals=2,
            away_goals=0,
        )
        self.assertFalse(unchanged_bet.is_updated())

    def test_bet_is_updated_for_changed_bet(self):
        creation_time = timezone.now() - timezone.timedelta(days=1)

        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = creation_time

            bet = Bet.objects.create(
                game=self.game2,
                user=self.user,
                home_goals=1,
                away_goals=2,
            )

        self.assertFalse(bet.is_updated())

        bet.home_goals = 3
        bet.away_goals = 2
        bet.save()
        self.assertTrue(bet.is_updated())

    def test_bet_can_be_placed_when_game_has_not_started(self):
        bet = Bet.objects.create(
            game=self.game1,
            user=self.user,
            home_goals=2,
            away_goals=0,
        )
        
        self.assertIsNotNone(bet.id)

    def test_bet_cannot_be_placed_when_game_has_started(self):
        game = Game.objects.create(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() - timezone.timedelta(hours=1),
        )
        bet = Bet(
            game=game,
            user=self.user,
            home_goals=2,
            away_goals=0,
        )
        with self.assertRaises(ValidationError):
            bet.full_clean()

class StandingPredictionModelTest(TestCase):
    def setUp(self):
        # Create some related objects for testing
        self.user = get_user_model().objects.create_user(
            username = 'testuser',
            password = 'testpassword',
        )
        self.team1 = Team.objects.create(name='Manchester United')
        self.team2 = Team.objects.create(name='Arsenal')
        self.team3 = Team.objects.create(name='Chelsea')
        self.team4 = Team.objects.create(name='Liverpool')
        self.team5 = Team.objects.create(name='Manchester City')
        self.team6 = Team.objects.create(name='Tottenham Hotspur')
        self.team7 = Team.objects.create(name='Leicester City')
        self.team8 = Team.objects.create(name='West Ham United')
        self.team9 = Team.objects.create(name='Everton')
        self.team10 = Team.objects.create(name='Aston Villa')
        self.team11 = Team.objects.create(name='Wolverhampton Wanderers')
        self.team12 = Team.objects.create(name='Crystal Palace')
        self.competition = Competition.objects.create(name='Premier League', season='23/24')
        self.competition.teams.add(self.team1, self.team2, self.team3, self.team4, self.team5, self.team6, self.team7, self.team8, self.team9, self.team10, self.team11, self.team12)
        self.standing_prediction = StandingPrediction.objects.create(user=self.user, competition=self.competition)

    # def test_standing_prediction_calculate_points_without_standing(self):
    #     self.assertEqual(self.standing_prediction.calculate_points(), 0)

    # def test_standing_prediction_calculate_points_with_standing(self):
    #     self.standing = Standing.objects.create(competition=self.competition, round=1)
    #     self.assertEqual(self.standing_prediction.calculate_points(), 0)

    # def test_standing_prediction_calculate_points_with_standing_and_team_positions(self):
    #     self.standing = Standing.objects.create(competition=self.competition, round=1)
    #     self.team_position1 = TeamPosition.objects.create(standing=self.standing, team=self.team1, position=1)
    #     self.team_position2 = TeamPosition.objects.create(standing=self.standing, team=self.team2, position=2)
    #     self.assertEqual(self.standing_prediction.calculate_points(), 0)

    # def test_standing_prediction_calculate_points_one_correct(self):
    #     self.standing = Standing.objects.create(competition=self.competition, round=1)
    #     self.team_position1 = TeamPosition.objects.create(standing=self.standing, team=self.team1, position=5)
    #     self.team_position2 = TeamPosition.objects.create(standing=self.standing, team=self.team2, position=6)
    #     self.team_position3 = TeamPosition.objects.create(standing=self.standing, team=self.team3, position=7)
    #     self.team_position4 = TeamPosition.objects.create(standing=self.standing, team=self.team4, position=8)
    #     self.team_position5 = TeamPosition.objects.create(standing=self.standing, team=self.team5, position=1)
    #     self.team_position6 = TeamPosition.objects.create(standing=self.standing, team=self.team6, position=10)
    #     self.team_position7 = TeamPosition.objects.create(standing=self.standing, team=self.team7, position=11)
    #     self.team_position8 = TeamPosition.objects.create(standing=self.standing, team=self.team8, position=12)
    #     self.team_position9 = TeamPosition.objects.create(standing=self.standing, team=self.team9, position=9)
    #     self.team_position10 = TeamPosition.objects.create(standing=self.standing, team=self.team10, position=2)
    #     self.team_position11 = TeamPosition.objects.create(standing=self.standing, team=self.team11, position=3)
    #     self.team_position12 = TeamPosition.objects.create(standing=self.standing, team=self.team12, position=4)
    #     self.standing_prediction_team1 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team1, position=1)
    #     self.standing_prediction_team2 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team2, position=2)
    #     self.standing_prediction_team3 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team3, position=3)
    #     self.standing_prediction_team4 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team4, position=4)
    #     self.standing_prediction_team5 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team5, position=5)
    #     self.standing_prediction_team6 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team6, position=6)
    #     self.standing_prediction_team7 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team7, position=7)
    #     self.standing_prediction_team8 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team8, position=8)
    #     self.standing_prediction_team9 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team9, position=9)
    #     self.standing_prediction_team10 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team10, position=10)
    #     self.standing_prediction_team11 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team11, position=11)
    #     self.standing_prediction_team12 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team12, position=12)
    #     self.standing_prediction.team_positions.add(self.standing_prediction_team1, self.standing_prediction_team2, self.standing_prediction_team3, self.standing_prediction_team4, self.standing_prediction_team5, self.standing_prediction_team6, self.standing_prediction_team7, self.standing_prediction_team8, self.standing_prediction_team9, self.standing_prediction_team10, self.standing_prediction_team11, self.standing_prediction_team12)
    #     self.assertEqual(self.standing_prediction.calculate_points(), 6)

    # def test_standing_prediction_calculate_points_one_almost_correct(self):
    #     self.standing = Standing.objects.create(competition=self.competition, round=1)
    #     self.team_position1 = TeamPosition.objects.create(standing=self.standing, team=self.team1, position=5)
    #     self.team_position2 = TeamPosition.objects.create(standing=self.standing, team=self.team2, position=6)
    #     self.team_position3 = TeamPosition.objects.create(standing=self.standing, team=self.team3, position=7)
    #     self.team_position4 = TeamPosition.objects.create(standing=self.standing, team=self.team4, position=8)
    #     self.team_position5 = TeamPosition.objects.create(standing=self.standing, team=self.team5, position=2)
    #     self.team_position6 = TeamPosition.objects.create(standing=self.standing, team=self.team6, position=10)
    #     self.team_position7 = TeamPosition.objects.create(standing=self.standing, team=self.team7, position=11)
    #     self.team_position8 = TeamPosition.objects.create(standing=self.standing, team=self.team8, position=12)
    #     self.team_position9 = TeamPosition.objects.create(standing=self.standing, team=self.team9, position=1)
    #     self.team_position10 = TeamPosition.objects.create(standing=self.standing, team=self.team10, position=9)
    #     self.team_position11 = TeamPosition.objects.create(standing=self.standing, team=self.team11, position=3)
    #     self.team_position12 = TeamPosition.objects.create(standing=self.standing, team=self.team12, position=4)
    #     self.standing_prediction_team1 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team1, position=1)
    #     self.standing_prediction_team2 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team2, position=2)
    #     self.standing_prediction_team3 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team3, position=3)
    #     self.standing_prediction_team4 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team4, position=4)
    #     self.standing_prediction_team5 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team5, position=5)
    #     self.standing_prediction_team6 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team6, position=6)
    #     self.standing_prediction_team7 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team7, position=7)
    #     self.standing_prediction_team8 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team8, position=8)
    #     self.standing_prediction_team9 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team9, position=9)
    #     self.standing_prediction_team10 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team10, position=10)
    #     self.standing_prediction_team11 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team11, position=11)
    #     self.standing_prediction_team12 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team12, position=12)
    #     self.standing_prediction.team_positions.add(self.standing_prediction_team1, self.standing_prediction_team2, self.standing_prediction_team3, self.standing_prediction_team4, self.standing_prediction_team5, self.standing_prediction_team6, self.standing_prediction_team7, self.standing_prediction_team8, self.standing_prediction_team9, self.standing_prediction_team10, self.standing_prediction_team11, self.standing_prediction_team12)
    #     self.assertEqual(self.standing_prediction.calculate_points(), 2)

    # def test_standing_prediction_calculate_points_mixed_results(self):
    #     self.standing = Standing.objects.create(competition=self.competition, round=1)
    #     self.team_position1 = TeamPosition.objects.create(standing=self.standing, team=self.team1, position=1)
    #     self.team_position2 = TeamPosition.objects.create(standing=self.standing, team=self.team2, position=3)
    #     self.team_position3 = TeamPosition.objects.create(standing=self.standing, team=self.team3, position=7)
    #     self.team_position4 = TeamPosition.objects.create(standing=self.standing, team=self.team4, position=8)
    #     self.team_position5 = TeamPosition.objects.create(standing=self.standing, team=self.team5, position=2)
    #     self.team_position6 = TeamPosition.objects.create(standing=self.standing, team=self.team6, position=4)
    #     self.team_position7 = TeamPosition.objects.create(standing=self.standing, team=self.team7, position=5)
    #     self.team_position8 = TeamPosition.objects.create(standing=self.standing, team=self.team8, position=10)
    #     self.team_position9 = TeamPosition.objects.create(standing=self.standing, team=self.team9, position=6)
    #     self.team_position10 = TeamPosition.objects.create(standing=self.standing, team=self.team10, position=12)
    #     self.team_position11 = TeamPosition.objects.create(standing=self.standing, team=self.team11, position=11)
    #     self.team_position12 = TeamPosition.objects.create(standing=self.standing, team=self.team12, position=9)
    #     self.standing_prediction_team1 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team1, position=1)
    #     self.standing_prediction_team2 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team2, position=2)
    #     self.standing_prediction_team3 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team3, position=3)
    #     self.standing_prediction_team4 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team4, position=4)
    #     self.standing_prediction_team5 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team5, position=5)
    #     self.standing_prediction_team6 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team6, position=6)
    #     self.standing_prediction_team7 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team7, position=7)
    #     self.standing_prediction_team8 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team8, position=8)
    #     self.standing_prediction_team9 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team9, position=9)
    #     self.standing_prediction_team10 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team10, position=10)
    #     self.standing_prediction_team11 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team11, position=11)
    #     self.standing_prediction_team12 = StandingPredictionTeam.objects.create(standing_prediction=self.standing_prediction, team=self.team12, position=12)
    #     self.standing_prediction.team_positions.add(self.standing_prediction_team1, self.standing_prediction_team2, self.standing_prediction_team3, self.standing_prediction_team4, self.standing_prediction_team5, self.standing_prediction_team6, self.standing_prediction_team7, self.standing_prediction_team8, self.standing_prediction_team9, self.standing_prediction_team10, self.standing_prediction_team11, self.standing_prediction_team12)
    #     self.assertEqual(self.standing_prediction.calculate_points(), 18)
