from django import forms
from .models import *

class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonials
        fields = ['name', 'message']
