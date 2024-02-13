from django.forms import ModelForm, Form, ChoiceField, Select
from .models import Team, Game, Bet, StandingPrediction

class CustomModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

class YearSelectionForm(Form):
    def __init__(self, *args, **kwargs):
        super(YearSelectionForm, self).__init__(*args, **kwargs)
        self.fields['year'] = ChoiceField(
            choices=sorted([(date.year, date.year) for date in Game.objects.dates('start_time', 'year') if Game.objects.exists()], reverse=True),
            widget=Select(attrs={'class': 'custom-select'})
        )


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
        fields = ['top_scorer', 'most_assists']
