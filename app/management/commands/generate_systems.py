from django.core.management.base import BaseCommand, CommandError
from app.models import *
from app.constants import *
import time
import random
from app.map_settings import *
from django.db import transaction



class Command(BaseCommand): # must be called command, use file name to name the functionality
    @transaction.atomic
    def handle(self, *args, **options):
        start_t = time.time()
        System.objects.all().delete()
        planets = Planet.objects.all().order_by('x', 'y')
        for p in planets:
            system = System.objects.filter(x=p.x, y=p.y).first()
            if system is None:
                System.objects.create(x=p.x, y=p.y)
        systems = System.objects.all()
        for s in systems:
            if s.id % 10 == 0 or s.id % 10 == 5:
                s.img = "/static/map/s1.png"
            if s.id % 10 == 1 or s.id % 10 == 6:
                s.img = "/static/map/s2.png"
            if s.id % 10 == 2 or s.id % 10 == 7:
                s.img = "/static/map/s3.png"
            if s.id % 10 == 3 or s.id % 10 == 8:
                s.img = "/static/map/s4.png"
            if s.id % 10 == 4 or s.id % 10 == 9:
                s.img = "/static/map/s5.png"
            s.save()

        print("Generating systems took " + str(time.time() - start_t) + "seconds")
