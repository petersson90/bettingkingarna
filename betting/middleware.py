from django.shortcuts import redirect
from .forms import YearSelectionForm
from .models import Game

class SelectedYearMiddleware:
    ''' Adding the selected year as a variable to each view '''
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the latest available year
        latest_year = Game.objects.latest('start_time').start_time.year if Game.objects.exists() else None

        # Retrieve the user's selected year from the session or use the latest year
        selected_year = request.session.get('selected_year', latest_year)

        if request.method == 'POST':
            form = YearSelectionForm(request.POST)
            if form.is_valid():
                selected_year = form.cleaned_data['year']
                request.session['selected_year'] = selected_year

                return redirect(request.path)

        # Set the selected_year in the request object
        request.selected_year = request.session.get('selected_year')

        response = self.get_response(request)

        return response
