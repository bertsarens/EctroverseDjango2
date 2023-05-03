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
        arte = Artefacts.objects.get(name="Terraformer")
        
        choosebonus = random.randint(1,5)
        bonus = random.randint(10,100)
        if arte.empire_holding != None:
            for player in UserStatus.objects.all():
                if player.empire == arte.empire_holding:
                    planet = []
                    plcount = 0
                    pl = Planet.objects.filter(home_planet=False, bonus_solar='0', bonus_mineral='0', bonus_crystal='0', bonus_ectrolium='0', bonus_fission = '0', owner=player.id, artefact=None)
                    for p in pl:
                        planet.append(p)
                        plcount += 1
                    if plcount == 0:
                        if choosebonus == 1:
                            planet = random.choice(Planet.objects.filter(home_planet=False, bonus_solar__gte=1, owner=player.id, artefact=None))
                        if choosebonus == 2:
                            planet = random.choice(Planet.objects.filter(home_planet=False, bonus_crystal__gte=1, owner=player.id, artefact=None))
                        if choosebonus == 3:
                            planet = random.choice(Planet.objects.filter(home_planet=False, bonus_mineral__gte=1, owner=player.id, artefact=None))
                        if choosebonus == 4:
                            planet = random.choice(Planet.objects.filter(home_planet=False, bonus_ectrolium__gte=1, owner=player.id, artefact=None))
                        if choosebonus == 5:
                            planet = random.choice(Planet.objects.filter(home_planet=False, bonus_fission__gte=1, owner=player.id, artefact=None))
                    else:
                        planet = random.choice(planet)
                    if choosebonus == 1:
                        planet.bonus_solar += bonus
                        planet.save()
                    elif choosebonus == 2:
                        planet.bonus_crystal += bonus
                        planet.save()
                    elif choosebonus == 3:
                        planet.bonus_mineral += bonus
                        planet.save()
                    elif choosebonus == 4:
                        planet.bonus_ectrolium += bonus
                        planet.save()
                    elif choosebonus == 5:
                        planet.bonus_fission += bonus
                        planet.save()
                    print(planet)
            ticks = random.randint(10, 144)
            arte.ticks_left = ticks
            arte.save()
        print("Generating terraformer took " + str(time.time() - start_t) + "seconds")
