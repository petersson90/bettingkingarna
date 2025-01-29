from django import template

register = template.Library()

@register.filter
def get_dynamic_key(row, key):
    return row.get(f'user_{key}_cumulative_points', 0)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, None)