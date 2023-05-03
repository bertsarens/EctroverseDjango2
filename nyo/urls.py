from django.urls import path
from nyo import views

urlpatterns = [
    path('', views.index),
    path('testimonials', views.testimonials, name='testimonials'),
    path('contact', views.contact, name='contact'),
    path('addtest', views.addtest, name='addtest'),
]
