from django.forms import ModelForm
from .models import Bet

class BetForm(ModelForm):
    class Meta:
        model = Bet
        fields = ['home_goals', 'away_goals'] # '__all__' # 
