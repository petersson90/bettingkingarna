from django.forms import ModelForm
from .models import Team, Game, Bet

        
class GameForm(ModelForm):
    class Meta:
        model = Game
        fields = '__all__'


class TeamForm(ModelForm):
    class Meta:
        model = Team
        fields = '__all__'


class BetForm(ModelForm):
    class Meta:
        model = Bet
        fields = ['home_goals', 'away_goals'] # '__all__' # 
