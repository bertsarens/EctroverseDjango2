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
        solar = 150
        mineral = 75
        crystal = 50
        ectrolium = 50
        for _ in range(solar):
            planet = random.choice(Planet.objects.filter(home_planet=False, bonus_solar='0', bonus_mineral='0', bonus_crystal='0', bonus_ectrolium='0', artefact=None))
            bonus = random.randint(10,100)
            planet.bonus_solar += bonus
            planet.save()
        for _ in range(crystal):
            planet = random.choice(Planet.objects.filter(home_planet=False, bonus_solar='0', bonus_mineral='0', bonus_crystal='0', bonus_ectrolium='0', artefact=None))
            bonus = random.randint(10,100)
            planet.bonus_crystal += bonus
            planet.save()
        for _ in range(mineral):
            planet = random.choice(Planet.objects.filter(home_planet=False, bonus_solar='0', bonus_mineral='0', bonus_crystal='0', bonus_ectrolium='0', artefact=None))
            bonus = random.randint(10,100)
            planet.bonus_mineral += bonus
            planet.save()
        for _ in range(ectrolium):
            planet = random.choice(Planet.objects.filter(home_planet=False, bonus_solar='0', bonus_mineral='0', bonus_crystal='0', bonus_ectrolium='0', artefact=None))
            bonus = random.randint(10,100)
            planet.bonus_ectrolium += bonus
            planet.save()

        print("Generating bonuses took " + str(time.time() - start_t) + "seconds")
