from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from app.models import *
from app.calculations import *
from app.constants import *
import time
from django.db.models import Q
from django.db import connection
from app.helper_functions import *
import random



class Command(BaseCommand): # must be called command, use file name to name the functionality
    @transaction.atomic
    def handle(self, *args, **options):
        for status in UserStatus.objects.all():
            if status.networth == 0 or not status.empire:
                continue
            portal_xy_list = Planet.objects.filter(portal=True, owner=status.user.id).values_list('x', 'y')
            planets_buffer = Planet.objects.filter(owner=status.user.id)
            for planet in planets_buffer:
                if planet.portal:
                    planet.protection = 100
                else:
                    planet.protection = min(100, int(100.0 * battlePortalCalc(planet.x, planet.y, portal_xy_list, status.research_percent_portals)))
                planet.save()
                if Construction.objects.filter(planet=planet).exists():
                    continue
                else:
                    planet.buildings_under_construction = 0
                    planet.save()
                if Specops.objects.filter(planet=planet, name='Portal Force Field').exists():
                    for op in Specops.objects.filter(planet=planet, name='Portal Force Field'):
                        strength = op.specop_strength
                        effect = planet.protection * (strength/100)
                        planet.protection -= effect
                        planet.save()
                planet.popper = planet.current_population / planet.max_population * 100
                planet.save()
            for sh in Specops.objects.filter(user_to=status.user, name='Vortex Portal'): 
                status.num_planets = (status.num_planets - 1)
                status.empire.planets = status.num_planets
                status.save()
                status.empire.save()

                        
            	    
