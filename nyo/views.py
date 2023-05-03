from django.shortcuts import render, HttpResponse, HttpResponseRedirect
from .models import *
from .forms import *
# Create your views here.

def index(request):
    return render(request, "home.html")

def testimonials(request):
    testis = Testimonials.objects.all()
    return render(request, "testimonials.html", {'testis':testis,})
    
def contact(request):
    return render(request, "contact.html")
    
def addtest(request):
    context = {}

    form = TestimonialForm(request.POST)
    if form.is_valid():
            print('valid')
            form.save()
            return HttpResponseRedirect('/nyo/testimonials')
    context['form']= form
    return render(request, "addtest.html", context)
