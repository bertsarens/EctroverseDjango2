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
        exclude_list = ['1','3','4','5','6','7','8']
        user = UserStatus.objects.all().exclude(id__in=exclude_list)
        for u in user:
            if u.tag_points >= 12500:
            	u.tag = "personalized tag"
            elif u.tag_points >= 9000:
                u.tag = "Transcend"
            elif u.tag_points >= 7000:
                u.tag = "Master Wizard"
            elif u.tag_points >= 5800:
                u.tag = "Dear Leader"
            elif u.tag_points >= 4600:
                u.tag = "Fleet Admiral"            
            elif u.tag_points >= 3900:
                u.tag = "Squadron Commander"
            elif u.tag_points >= 3500:
                u.tag = "Cruiser Captain"
            elif u.tag_points >= 3100:
                u.tag = "Wing Commander"                                        
            elif u.tag_points >= 2600:
                u.tag = "Lieutenant Commander"
            elif u.tag_points >= 2250:
                u.tag = "Squad Lieutenant"
            elif u.tag_points >= 1700:
                u.tag = "Patrol Officer"                
            elif u.tag_points >= 1320:
                u.tag = "1st Officer"                
            elif u.tag_points >= 1150:
                u.tag = "2nd Officer"                
            elif u.tag_points >= 850:
                u.tag = "3rd Officer"                
            elif u.tag_points >= 600:
                u.tag = "Master-at-Arms"                
            elif u.tag_points >= 460:
                u.tag = "Helmsman"                
            elif u.tag_points >= 380:
                u.tag = "1st Technician"                
            elif u.tag_points >= 240:
                u.tag = "2nd Technician"                
            elif u.tag_points >= 160:
                u.tag = "3rd Technician"
            elif u.tag_points >= 80:
                u.tag = "Chicken-soup-machine Repairman"                
            elif u.tag_points >= 45:
                u.tag = "Veteran"                
            else:
                u.tag = "Player"
            u.save()     
        for p in Planet.objects.all():
            if Planet.objects.filter(x=p.x, y=p.y, i=p.i).count() > 1:
                print(str(p.id))
                if p.home_planet == False:
                    p.delete()
                   
                
                                                
        print("Generating settings took " + str(time.time() - start_t) + "seconds")
