from django.forms import ModelForm, ChoiceField, Select, ValidationError
from .models import Team, Competition, Game, Bet, StandingPrediction

class CustomModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

        
class GameForm(CustomModelForm):
    class Meta:
        model = Game
        fields = '__all__'


class TeamForm(CustomModelForm):
    class Meta:
        model = Team
        fields = '__all__'


class BetForm(CustomModelForm):
    class Meta:
        model = Bet
        fields = ['home_goals', 'away_goals']


class StandingPredictionForm(CustomModelForm):
    def __init__(self, *args, **kwargs):
        competition = kwargs.pop('competition', None)
        super().__init__(*args, **kwargs)
        instance = kwargs.pop('instance', None)
        
        # if instance:
        #     team_ids = [int(team_id) for team_id in instance.standing.split(',')]
        #     print(team_ids)
        #     teams = Team.objects.filter(id__in=team_ids)
        #     team_names = [team.name for team in teams]
        #     for i, team_name in enumerate(team_names):
        #         self.fields[f'position_{i+1}'].initial = team_name
        #     competition = instance.competition
        # else:
        #     competition = kwargs.pop('competition', None)
        
        teams = competition.teams.all()
        positions = range(1, len(teams) + 1)
        choices = [(team.id, team.name) for team in teams]
        for i in positions:
            self.fields[f'position_{i}'] = ChoiceField(
                label=f'{i}.',
                choices=choices,
                widget=Select(attrs={'class': 'form-control'})
            )

    class Meta:
        model = StandingPrediction
        exclude = ['user', 'competition', 'standing', 'created', 'updated']
