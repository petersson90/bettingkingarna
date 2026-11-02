import os
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Bet, Team, Competition, Game, Standing, StandingPrediction, StandingPredictionTeam, TeamPosition, calculate_extra_bet, calculate_extra_bet_outcomes, calculate_position_bounds
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
        team = Team.objects.create(name='Malmö FF')
        self.assertEqual(str(team), 'Malmö FF')

    def test_team_with_logo(self):
        logo = SimpleUploadedFile('test_logo.svg', b'file_content', content_type='image/svg+xml')
        team = Team.objects.create(name='AIK', logo=logo)
        self.assertIsNotNone(team.id)
        self.assertEqual(team.name, 'AIK')
        self.assertIsNotNone(team.logo)
        self.assertEqual(team.logo.name, 'team_logos/test_logo.svg')


class CompetitionModelTest(TestCase):
    def setUp(self):
        self.team1 = Team.objects.create(name="Malmö FF")
        self.team2 = Team.objects.create(name="IFK Göteborg")
        self.team3 = Team.objects.create(name="AIK")

    def test_competition_string_representation(self):
        current_year = timezone.now().year
        competition = Competition.objects.create(name="Allsvenskan", season=current_year)
        self.assertEqual(str(competition), f"Allsvenskan {current_year}")
    
    def test_competition_cannot_have_duplicate_teams(self):
        current_year = timezone.now().year
        competition = Competition.objects.create(name="Allsvenskan", season=current_year)
        self.assertEqual(competition.teams.count(), 0)
        competition.teams.add(self.team1, self.team1)
        self.assertEqual(competition.teams.count(), 1)


class GameModelTest(TestCase):
    def setUp(self):
        current_year = timezone.now().year
        self.team1 = Team.objects.create(name="Malmö FF")
        self.team2 = Team.objects.create(name="IFK Göteborg")
        self.competition = Competition.objects.create(name="Allsvenskan", season=current_year)

    def test_game_string_representation(self):
        game = Game.objects.create(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() + timezone.timedelta(hours=1),
        )
        self.assertEqual(str(game), "Malmö FF - IFK Göteborg")

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
        current_year = timezone.now().year
        # Create some related objects for testing
        self.user = get_user_model().objects.create_user(
            username = 'testuser',
            password = 'testpassword',
        )
        self.team1 = Team.objects.create(name='Malmö FF')
        self.team2 = Team.objects.create(name='IFK Göteborg')
        self.competition = Competition.objects.create(name='Allsvenskan', season=current_year)
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
        current_year = timezone.now().year
        # Create some related objects for testing
        self.user = get_user_model().objects.create_user(
            username = 'testuser',
            password = 'testpassword',
        )
        self.team1 = Team.objects.create(name='Malmö FF')
        self.team2 = Team.objects.create(name='IFK Göteborg')
        self.team3 = Team.objects.create(name='AIK')
        self.team4 = Team.objects.create(name='Djurgårdens IF')
        self.team5 = Team.objects.create(name='IFK Norrköping')
        self.team6 = Team.objects.create(name='IF Elfsborg')
        self.team7 = Team.objects.create(name='Hammarby IF')
        self.team8 = Team.objects.create(name='Örebro SK')
        self.team9 = Team.objects.create(name='Kalmar FF')
        self.team10 = Team.objects.create(name='Östersunds FK')
        self.team11 = Team.objects.create(name='Helsingborgs IF')
        self.team12 = Team.objects.create(name='GIF Sundsvall')
        self.competition = Competition.objects.create(name='Allsvenskan', season=current_year)
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


class CalculateExtraBetTest(TestCase):
    ''' Pure-function tests for calculate_extra_bet - no DB involved. Arguments are
    (most points prediction, clean sheets prediction, who wins most points, final clean sheets).
    '''

    def test_no_predictions_gives_no_points(self):
        self.assertEqual(calculate_extra_bet('', None, 'Jane Doe', 8), 0)

    def test_correct_most_points_pick_gives_six(self):
        self.assertEqual(calculate_extra_bet('Jane Doe', None, 'Jane Doe', 8), 6)

    def test_wrong_most_points_pick_gives_nothing(self):
        self.assertEqual(calculate_extra_bet('John Smith', None, 'Jane Doe', 8), 0)

    def test_only_the_first_pick_counts(self):
        self.assertEqual(calculate_extra_bet('Jane Doe, John Smith', None, 'Jane Doe', 8), 6)
        self.assertEqual(calculate_extra_bet('John Smith, Jane Doe', None, 'Jane Doe', 8), 0)

    def test_picks_can_be_separated_without_a_space(self):
        self.assertEqual(calculate_extra_bet('Jane Doe,John Smith', None, 'Jane Doe', 8), 6)

    def test_nobody_winning_gives_no_most_points_bonus(self):
        self.assertEqual(calculate_extra_bet('Jane Doe', None, None, 8), 0)

    def test_clean_sheets_penalty_is_the_distance_to_the_prediction(self):
        self.assertEqual(calculate_extra_bet('', 7, None, 5), -2)
        self.assertEqual(calculate_extra_bet('', 7, None, 10), -3)
        self.assertEqual(calculate_extra_bet('', 7, None, 7), 0)

    def test_clean_sheets_are_not_scored_while_either_value_is_empty_or_zero(self):
        # Mirrors the live scoring, which skips the clean sheets term for empty/0 values.
        self.assertEqual(calculate_extra_bet('', None, None, 5), 0)
        self.assertEqual(calculate_extra_bet('', 0, None, 5), 0)
        self.assertEqual(calculate_extra_bet('', 7, None, 0), 0)

    def test_most_points_and_clean_sheets_are_combined(self):
        self.assertEqual(calculate_extra_bet('Jane Doe', 7, 'Jane Doe', 5), 4)


class CalculateExtraBetOutcomesTest(TestCase):
    ''' Pure-function tests for calculate_extra_bet_outcomes - no DB involved.
    Predictions are {user: (most points prediction, clean sheets prediction)}.
    '''

    def test_covers_every_winner_and_every_reachable_clean_sheets_value(self):
        outcomes = calculate_extra_bet_outcomes({'A': ('Jane Doe', 7), 'B': ('John Smith', 5)}, 5, 2)
        # 3 winners (Jane Doe, John Smith, somebody nobody picked) x 3 clean sheets values (5-7).
        self.assertEqual(len(outcomes), 9)

    def test_a_users_range_follows_the_rules_for_most_points_and_clean_sheets(self):
        outcomes = calculate_extra_bet_outcomes({'A': ('Jane Doe', 7)}, 5, 3)
        values = [outcome['A'] for outcome in outcomes]
        # Final clean sheets 5-8 give penalties 2, 1, 0, 1. The bonus of 6 needs Jane Doe to win.
        self.assertEqual((min(values), max(values)), (-2, 6))

    def test_users_with_the_same_bet_always_score_the_same(self):
        predictions = {'A': ('Jane Doe', 7), 'B': ('Jane Doe', 7), 'C': ('John Smith', 5)}
        outcomes = calculate_extra_bet_outcomes(predictions, 5, 3)
        self.assertTrue(all(outcome['A'] == outcome['B'] for outcome in outcomes))
        self.assertTrue(any(outcome['A'] != outcome['C'] for outcome in outcomes))

    def test_blank_predictions_are_ignored(self):
        outcomes = calculate_extra_bet_outcomes({'A': ('', None)}, 5, 2)
        self.assertEqual(len(outcomes), 3)
        self.assertEqual({outcome['A'] for outcome in outcomes}, {0})

    def test_missing_current_clean_sheets_count_as_zero(self):
        outcomes = calculate_extra_bet_outcomes({'A': ('', 2)}, None, 3)
        # Final clean sheets 0-3: not scored at 0, then 1 off, exact, 1 off.
        self.assertEqual(sorted(outcome['A'] for outcome in outcomes), [-1, -1, 0, 0])

    def test_no_remaining_games_leaves_a_single_clean_sheets_value(self):
        outcomes = calculate_extra_bet_outcomes({'A': ('Jane Doe', 7)}, 5, 0)
        self.assertEqual(sorted(outcome['A'] for outcome in outcomes), [-2, 4])


class CalculatePositionBoundsTest(TestCase):
    ''' Pure-function tests for calculate_position_bounds - no DB involved.
    Arguments are the settled points per user, the joint extra bet outcomes and the most
    match points anyone can still add.
    '''

    def test_fixed_totals_give_the_current_ranking(self):
        bounds = calculate_position_bounds({'A': 30, 'B': 20, 'C': 10}, [{}], 0)
        self.assertEqual(bounds['A'], {'best_rank': 1, 'worst_rank': 1})
        self.assertEqual(bounds['B'], {'best_rank': 2, 'worst_rank': 2})
        self.assertEqual(bounds['C'], {'best_rank': 3, 'worst_rank': 3})

    def test_no_outcomes_means_no_extra_points(self):
        self.assertEqual(
            calculate_position_bounds({'A': 30, 'B': 20}, [], 0),
            calculate_position_bounds({'A': 30, 'B': 20}, [{}], 0),
        )

    def test_a_big_enough_lead_locks_in_the_final_ranking(self):
        bounds = calculate_position_bounds({'leader': 100, 'chaser': 0}, [{}], 6)
        self.assertEqual(bounds['leader'], {'best_rank': 1, 'worst_rank': 1})
        self.assertEqual(bounds['chaser'], {'best_rank': 2, 'worst_rank': 2})

    def test_overlapping_ranges_leave_both_users_ranks_uncertain(self):
        bounds = calculate_position_bounds({'A': 10, 'B': 8}, [{}], 6)
        self.assertEqual(bounds['A'], {'best_rank': 1, 'worst_rank': 2})
        self.assertEqual(bounds['B'], {'best_rank': 1, 'worst_rank': 2})

    def test_extra_bet_outcomes_can_change_the_ranking(self):
        outcomes = [{'A': 0, 'B': 0}, {'A': 0, 'B': 11}]
        bounds = calculate_position_bounds({'A': 10, 'B': 0}, outcomes, 0)
        self.assertEqual(bounds['A'], {'best_rank': 1, 'worst_rank': 2})
        self.assertEqual(bounds['B'], {'best_rank': 1, 'worst_rank': 2})

    def test_exact_ties_are_not_counted_against_a_user(self):
        bounds = calculate_position_bounds({'A': 10, 'B': 10}, [{}], 0)
        self.assertEqual(bounds['A'], {'best_rank': 1, 'worst_rank': 1})
        self.assertEqual(bounds['B'], {'best_rank': 1, 'worst_rank': 1})

    def test_users_with_the_same_extra_bet_never_split(self):
        # A and B have the same bet, so they gain or lose together. If they could be at
        # opposite extremes, A's worst rank would be 3 (B up, A down, C in between).
        outcomes = [
            {'A': 4, 'B': 4, 'C': 0},
            {'A': -2, 'B': -2, 'C': 6},
            {'A': -2, 'B': -2, 'C': 0},
        ]
        bounds = calculate_position_bounds({'A': 6, 'B': 6, 'C': 3}, outcomes, 0)
        self.assertEqual(bounds['A'], {'best_rank': 1, 'worst_rank': 2})
        self.assertEqual(bounds['B'], {'best_rank': 1, 'worst_rank': 2})
        self.assertEqual(bounds['C'], {'best_rank': 1, 'worst_rank': 3})


class PositionForecastViewTest(TestCase):
    ''' Covers the /standings/forecast/ page without any standing predictions: alice has
    6 match points, bob 3, and one game is still to come (6 more points at most).
    '''

    def setUp(self):
        current_year = timezone.now().year
        self.team1 = Team.objects.create(name='Malmö FF')
        self.team2 = Team.objects.create(name='IFK Göteborg')
        self.competition = Competition.objects.create(name='Allsvenskan', season=current_year)
        self.competition.teams.add(self.team1, self.team2)

        self.user_a = get_user_model().objects.create_user(username='alice', password='testpassword')
        self.user_b = get_user_model().objects.create_user(username='bob', password='testpassword')

        finished_game = Game.objects.create(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() - timezone.timedelta(days=1),
            home_goals=2,
            away_goals=1,
        )
        # Exact result -> 6 points.
        exact_bet = Bet(game=finished_game, user=self.user_a, home_goals=2, away_goals=1, updated=timezone.now())
        exact_bet.save(game_updated=True)
        # Correct outcome, wrong score -> 3 points.
        near_miss_bet = Bet(game=finished_game, user=self.user_b, home_goals=1, away_goals=0, updated=timezone.now())
        near_miss_bet.save(game_updated=True)

        # One game still to come this season.
        Game.objects.create(
            competition=self.competition,
            home_team=self.team2,
            away_team=self.team1,
            start_time=timezone.now() + timezone.timedelta(days=1),
        )

    def _rows_by_user(self):
        response = self.client.get(reverse('betting:position-forecast'))
        return {row['user']: row for row in response.context['result']}, response

    def test_counts_the_remaining_games_in_the_season(self):
        _, response = self._rows_by_user()
        self.assertEqual(response.context['remaining_games'], 1)

    def test_shows_current_totals_and_position(self):
        rows, _ = self._rows_by_user()
        self.assertEqual(rows[self.user_a]['total']['current'], 6)
        self.assertEqual(rows[self.user_a]['current_position'], 1)
        self.assertEqual(rows[self.user_b]['total']['current'], 3)
        self.assertEqual(rows[self.user_b]['current_position'], 2)

    def test_without_predictions_only_match_points_can_change(self):
        rows, _ = self._rows_by_user()
        self.assertEqual(rows[self.user_a]['match'], {'current': 6, 'lowest': 6, 'highest': 12})
        self.assertEqual(rows[self.user_a]['table'], {'current': 0, 'lowest': 0, 'highest': 0})
        self.assertEqual(rows[self.user_a]['extra'], {'current': 0, 'lowest': 0, 'highest': 0})
        self.assertEqual(rows[self.user_a]['total'], {'current': 6, 'lowest': 6, 'highest': 12})

    def test_both_users_could_still_finish_either_1st_or_2nd(self):
        # 3-point gap with 1 game left (max 6 points) - not yet decided either way.
        rows, _ = self._rows_by_user()
        self.assertEqual(rows[self.user_a]['best_rank'], 1)
        self.assertEqual(rows[self.user_a]['worst_rank'], 2)
        self.assertEqual(rows[self.user_b]['best_rank'], 1)
        self.assertEqual(rows[self.user_b]['worst_rank'], 2)


class PositionForecastBreakdownViewTest(TestCase):
    ''' Covers the per type breakdown (match, table, extra) on /standings/forecast/ with
    two games left (12 match points at most) and 5 clean sheets so far.
    '''

    def setUp(self):
        now = timezone.now()
        self.team1 = Team.objects.create(name='Malmö FF')
        self.team2 = Team.objects.create(name='IFK Göteborg')
        self.competition = Competition.objects.create(name='Allsvenskan', season=now.year)
        self.competition.teams.add(self.team1, self.team2)

        self.alice = get_user_model().objects.create_user(username='alice', password='testpassword')
        self.bob = get_user_model().objects.create_user(username='bob', password='testpassword')

        finished_game = Game.objects.create(
            competition=self.competition,
            home_team=self.team1,
            away_team=self.team2,
            start_time=now - timezone.timedelta(days=1),
            home_goals=2,
            away_goals=1,
        )
        Bet(game=finished_game, user=self.alice, home_goals=2, away_goals=1, updated=now).save(game_updated=True)  # 6 points
        Bet(game=finished_game, user=self.bob, home_goals=1, away_goals=0, updated=now).save(game_updated=True)  # 3 points

        for days in (1, 2):
            Game.objects.create(
                competition=self.competition,
                home_team=self.team2,
                away_team=self.team1,
                start_time=now + timezone.timedelta(days=days),
            )

        # The current table has IFK Göteborg first and Malmö FF second.
        standing = Standing.objects.create(competition=self.competition, round=1, most_points='Jane Doe', clean_sheets=5)
        TeamPosition.objects.create(standing=standing, team=self.team2, position=1)
        TeamPosition.objects.create(standing=standing, team=self.team1, position=2)

        # Alice predicted the table the wrong way around, Jane Doe and 7 clean sheets.
        alice_prediction = StandingPrediction.objects.create(
            user=self.alice, competition=self.competition, most_points='Jane Doe', clean_sheets=7
        )
        StandingPredictionTeam.objects.create(standing_prediction=alice_prediction, team=self.team1, position=1)
        StandingPredictionTeam.objects.create(standing_prediction=alice_prediction, team=self.team2, position=2)
        # Bob picked John Smith and 5 clean sheets, and made no table prediction.
        StandingPrediction.objects.create(
            user=self.bob, competition=self.competition, most_points='John Smith', clean_sheets=5
        )

    def _rows_by_user(self):
        response = self.client.get(reverse('betting:position-forecast'))
        return {row['user']: row for row in response.context['result']}, response

    def test_match_points_range_from_the_current_points_to_six_per_remaining_game(self):
        rows, _ = self._rows_by_user()
        self.assertEqual(rows[self.alice]['match'], {'current': 6, 'lowest': 6, 'highest': 18})
        self.assertEqual(rows[self.bob]['match'], {'current': 3, 'lowest': 3, 'highest': 15})

    def test_table_points_are_static(self):
        rows, _ = self._rows_by_user()
        # Both teams are one position off: -1 and -1.
        self.assertEqual(rows[self.alice]['table'], {'current': -2, 'lowest': -2, 'highest': -2})
        self.assertEqual(rows[self.bob]['table'], {'current': 0, 'lowest': 0, 'highest': 0})

    def test_extra_points_range_over_most_points_and_clean_sheets(self):
        rows, _ = self._rows_by_user()
        # Alice has +6 and -2 for clean sheets today. Final clean sheets are 5-7, so the
        # best case is Jane Doe winning with 7 (+6) and the worst is not winning with 5 (-2).
        self.assertEqual(rows[self.alice]['extra'], {'current': 4, 'lowest': -2, 'highest': 6})
        # Bob has nothing today. His best case is John Smith winning with 5 clean sheets (+6).
        self.assertEqual(rows[self.bob]['extra'], {'current': 0, 'lowest': -2, 'highest': 6})

    def test_total_adds_up_the_parts(self):
        rows, _ = self._rows_by_user()
        self.assertEqual(rows[self.alice]['total'], {'current': 8, 'lowest': 2, 'highest': 22})
        self.assertEqual(rows[self.bob]['total'], {'current': 3, 'lowest': 1, 'highest': 21})

    def test_page_shows_the_current_value_with_its_range(self):
        _, response = self._rows_by_user()
        self.assertContains(response, '6 till 18')
        self.assertContains(response, '-2 till 6')
        self.assertNotContains(response, '-2 till -2')


class PositionForecastSharedBetViewTest(TestCase):
    ''' Covers two contestants with the same extra bet on /standings/forecast/. The season
    is over (no games left), so the last game played must count in the current points.
    '''

    def setUp(self):
        now = timezone.now()
        team1 = Team.objects.create(name='Malmö FF')
        team2 = Team.objects.create(name='IFK Göteborg')
        self.competition = Competition.objects.create(name='Allsvenskan', season=now.year)
        self.competition.teams.add(team1, team2)

        self.alice = get_user_model().objects.create_user(username='alice', password='testpassword')
        self.bob = get_user_model().objects.create_user(username='bob', password='testpassword')
        self.carol = get_user_model().objects.create_user(username='carol', password='testpassword')

        last_game = Game.objects.create(
            competition=self.competition,
            home_team=team1,
            away_team=team2,
            start_time=now - timezone.timedelta(days=1),
            home_goals=2,
            away_goals=1,
        )
        Bet(game=last_game, user=self.alice, home_goals=2, away_goals=1, updated=now).save(game_updated=True)  # 6 points
        Bet(game=last_game, user=self.bob, home_goals=2, away_goals=1, updated=now).save(game_updated=True)  # 6 points
        Bet(game=last_game, user=self.carol, home_goals=1, away_goals=0, updated=now).save(game_updated=True)  # 3 points

        Standing.objects.create(competition=self.competition, round=1, most_points='Jane Doe', clean_sheets=5)

        # Alice and Bob have the same extra bet, Carol picked someone else and is exact on clean sheets.
        for user in (self.alice, self.bob):
            StandingPrediction.objects.create(
                user=user, competition=self.competition, most_points='Jane Doe', clean_sheets=7
            )
        StandingPrediction.objects.create(
            user=self.carol, competition=self.competition, most_points='John Smith', clean_sheets=5
        )

    def _rows_by_user(self):
        response = self.client.get(reverse('betting:position-forecast'))
        return {row['user']: row for row in response.context['result']}, response

    def test_the_last_game_of_the_season_counts_in_the_current_points(self):
        rows, response = self._rows_by_user()
        self.assertEqual(response.context['remaining_games'], 0)
        self.assertEqual(rows[self.alice]['match'], {'current': 6, 'lowest': 6, 'highest': 6})
        self.assertEqual(rows[self.carol]['match'], {'current': 3, 'lowest': 3, 'highest': 3})

    def test_extra_ranges_come_from_the_shared_outcomes(self):
        rows, _ = self._rows_by_user()
        # Alice/Bob: +6 if Jane Doe wins, minus 2 for clean sheets (7 vs the final 5).
        self.assertEqual(rows[self.alice]['extra'], {'current': 4, 'lowest': -2, 'highest': 4})
        self.assertEqual(rows[self.bob]['extra'], {'current': 4, 'lowest': -2, 'highest': 4})
        self.assertEqual(rows[self.carol]['extra'], {'current': 0, 'lowest': 0, 'highest': 6})

    def test_contestants_with_the_same_bet_are_never_split_in_the_position_range(self):
        rows, _ = self._rows_by_user()
        # Jane Doe winning puts Alice and Bob on 10 together, anything else puts them on 4
        # together, so only Carol (9 if John Smith wins) can ever pass them: never both.
        self.assertEqual((rows[self.alice]['best_rank'], rows[self.alice]['worst_rank']), (1, 2))
        self.assertEqual((rows[self.bob]['best_rank'], rows[self.bob]['worst_rank']), (1, 2))
        self.assertEqual((rows[self.carol]['best_rank'], rows[self.carol]['worst_rank']), (1, 3))


class CalculateExtraBetWinnerTextTest(TestCase):
    ''' The winner is the text of the current standing, which can hold several names. '''

    def test_the_first_pick_is_found_in_a_two_name_winner_text(self):
        self.assertEqual(calculate_extra_bet('Jane Doe, John Smith', None, 'John Smith, Jane Doe', 8), 6)

    def test_a_blank_pick_never_matches_a_winner_text(self):
        self.assertEqual(calculate_extra_bet('', None, 'Jane Doe', 8), 0)

    def test_an_empty_winner_text_gives_no_bonus(self):
        self.assertEqual(calculate_extra_bet('Jane Doe', None, '', 8), 0)


class PositionForecastCurrentExtraViewTest(TestCase):
    ''' The current extra on /standings/forecast/ must lie inside its range, also when the
    live leaderboard would score it differently: a blank most points pick, a standing with
    top scorer/most assists filled in, and a winner text holding two names.
    One game is left, so the final clean sheets are 5 or 6.
    '''

    def setUp(self):
        now = timezone.now()
        team1 = Team.objects.create(name='Malmö FF')
        team2 = Team.objects.create(name='IFK Göteborg')
        self.competition = Competition.objects.create(name='Allsvenskan', season=now.year)
        self.competition.teams.add(team1, team2)

        finished_game = Game.objects.create(
            competition=self.competition,
            home_team=team1,
            away_team=team2,
            start_time=now - timezone.timedelta(days=1),
            home_goals=2,
            away_goals=1,
        )
        Game.objects.create(
            competition=self.competition,
            home_team=team2,
            away_team=team1,
            start_time=now + timezone.timedelta(days=1),
        )

        def contestant(username, most_points, clean_sheets):
            user = get_user_model().objects.create_user(username=username, password='testpassword')
            Bet(game=finished_game, user=user, home_goals=2, away_goals=1, updated=now).save(game_updated=True)
            StandingPrediction.objects.create(
                user=user, competition=self.competition, most_points=most_points, clean_sheets=clean_sheets
            )
            return user

        self.blank = contestant('blank', '', 7)
        self.other = contestant('other', 'John Smith', 7)
        self.both = contestant('both', 'Jane Doe, John Smith', 5)

        self.standing = Standing.objects.create(
            competition=self.competition,
            round=1,
            most_points='Jane Doe',
            clean_sheets=5,
            top_scorer='Some Scorer',
            most_assists='Some Assister',
        )

    def _rows_by_user(self):
        response = self.client.get(reverse('betting:position-forecast'))
        return {row['user']: row for row in response.context['result']}

    def _assert_inside_range(self, row):
        self.assertLessEqual(row['extra']['lowest'], row['extra']['current'])
        self.assertLessEqual(row['extra']['current'], row['extra']['highest'])

    def test_a_blank_most_points_pick_gives_no_bonus(self):
        row = self._rows_by_user()[self.blank]
        # Only the clean sheets term: 7 predicted against 5 so far.
        self.assertEqual(row['extra'], {'current': -2, 'lowest': -2, 'highest': -1})
        self._assert_inside_range(row)

    def test_top_scorer_and_most_assists_on_the_standing_are_not_scored(self):
        row = self._rows_by_user()[self.other]
        self.assertEqual(row['extra'], {'current': -2, 'lowest': -2, 'highest': 5})
        self._assert_inside_range(row)

    def test_two_picks_in_a_two_name_winner_text_give_a_single_bonus(self):
        Standing.objects.filter(pk=self.standing.pk).update(most_points='Jane Doe, John Smith')
        row = self._rows_by_user()[self.both]
        self.assertEqual(row['extra'], {'current': 6, 'lowest': -1, 'highest': 6})
        self._assert_inside_range(row)

    def test_current_total_is_the_sum_of_the_parts(self):
        for row in self._rows_by_user().values():
            self.assertEqual(
                row['total']['current'],
                row['match']['current'] + row['table']['current'] + row['extra']['current'],
            )


class PositionBoundsFromPredictionsTest(TestCase):
    ''' Outcomes and bounds together for predictions where the text differs but the bet is
    the same, because only the first name counts for most points.
    '''

    def test_only_the_first_name_of_each_user_is_a_possible_winner(self):
        predictions = {'A': ('Jane Doe, John Smith', 7), 'B': ('Jane Doe, Bob Brown', 7)}
        outcomes = calculate_extra_bet_outcomes(predictions, 5, 1)
        # Winners: Jane Doe or somebody nobody bet on (2) x clean sheets 5-6 (2).
        self.assertEqual(len(outcomes), 4)
        self.assertTrue(all(outcome['A'] == outcome['B'] for outcome in outcomes))

    def test_a_second_name_cannot_let_a_contestant_pass(self):
        # User 1: 87 match points, User 2: 68, 3 games (18 points) left, 10 clean sheets so far.
        predictions = {'U1': ('Hugo Bolin, Isak Jansson', 11), 'U2': ('Hugo Bolin, Pontus Wernbloom', 9)}
        outcomes = calculate_extra_bet_outcomes(predictions, 10, 3)
        bounds = calculate_position_bounds({'U1': 87, 'U2': 68}, outcomes, 18)
        self.assertEqual(bounds['U1'], {'best_rank': 1, 'worst_rank': 1})
        self.assertEqual(bounds['U2'], {'best_rank': 2, 'worst_rank': 2})