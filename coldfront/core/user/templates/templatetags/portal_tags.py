from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def get_version():
    return settings.VERSION


@register.simple_tag
def get_setting(name):
    return getattr(settings, name, "")

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, "")

@register.filter(name='replace')
def replace(value, arg):
    try:
        old, new = arg.split(',')
    except ValueError:
        return value
    return value.replace(old, new)