from django import template

register = template.Library()

@register.filter
def getvalue(h, key):
    return h[key]