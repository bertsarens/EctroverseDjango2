from django.db import models

class Testimonials(models.Model):
    name = models.CharField(max_length=50)
    message = models.CharField(max_length=500)

# Create your models here.
