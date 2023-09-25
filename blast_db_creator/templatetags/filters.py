import os
from django import template

register = template.Library()

# Creating a template filters and tags
@register.filter(name='get_dict_value')
def get_dict_value(dictionary, key):
    return dictionary.get(key)

@register.filter
def initialize(value=None):
    return value

@register.filter(name='basename')
def basename(location):
    return os.path.basename(str(location))