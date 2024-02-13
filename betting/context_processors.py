from .forms import YearSelectionForm

def year_selection(request):
    ''' Context processor to always include the year selection form '''
    # Retrieve the selected year from the request
    selected_year = request.selected_year

    form = YearSelectionForm(initial={'year': selected_year})

    return {'year_selection_form': form}
