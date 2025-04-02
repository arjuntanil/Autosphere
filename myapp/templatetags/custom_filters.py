from django import template
import random

register = template.Library()

@register.filter
def mask_chassis_number(value):
    """
    Masks the chassis number with asterisks while keeping some characters visible.
    For example, if the chassis number is "2974785", it will be displayed as "2**47*8*".
    """
    if not value:
        return value
    
    # Convert value to string in case it's not already
    chassis = str(value)
    
    # Keep the first character visible
    masked = chassis[0]
    
    # Mask about 60-70% of the remaining characters with asterisks
    for i in range(1, len(chassis)):
        # Keep some characters visible based on position
        if i % 3 == 0 or (i % 4 == 0 and i > 3):
            masked += chassis[i]
        else:
            masked += '*'
    
    return masked 

@register.filter
def absolute_value(value):
    """Return the absolute value of a number"""
    try:
        return abs(value) if value is not None else None
    except (ValueError, TypeError):
        return value 