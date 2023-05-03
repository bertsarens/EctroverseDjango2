from django.core.management.base import BaseCommand, CommandError
from app.models import *
from app.constants import *
import time
import random
from app.map_settings import *
from django.db import transaction

def artifacts():
    start_t = time.time()
    # delete old
    Artefacts.objects.all().delete()
    empires = Empire.objects.all()
    for e in empires:
        if e.artefacts is not None:
            e.artefacts.clear()
            e.save()
    planets = Planet.objects.filter(home_planet=False)
    for p in planets:
        if p.artefact is not None:
            p.artefact = None
            p.save()

    # add new
    # artefact list:
    arti_list = {
        "Ether Gardens": ["Increases your energy production by 10%!", 10, 0, 0, 0, "/static/arti/artimg0.gif"],
        "Mirny Mine": ["Increases your mineral production by 15%!", 15, 0, 0, 0 ,"/static/arti/artimg1.gif"],
        "Foohon Technology": ["Increases your ectrolium production by 10%!", 10, 0, 0, 0, "/static/arti/artimg2.gif"],
        "Crystal Synthesis": ["Increases your crystal production by 15%!", 15, 0, 0, 0, "/static/arti/artimg3.gif"],
        "Research Laboratory": ["Increases your research production by 10%!", 10, 0, 0, 0, "/static/arti/artimg4.gif"],
        "t-Veronica": ["A strange virus in the air improves your populations fighting ability!", 0, 0, 0, 0, "/static/arti/artimg5.gif"],
        "Darwinism": ["Citizens have evolved, aiding in the cause!", 0, 0, 0, 0, "/static/arti/artimg6.gif"],
        "Military Might": ["Decreases unit upkeep by 10%!", 10, 0, 0, 0, "/static/arti/artimg14.gif"],
        "Terraformer": ["An ancient gate allows planets to be transformed!", 0, 0, 0, 1, "/static/arti/artimg7.gif"],
        "The Recycler": ["Your scientist have developed a new technology, reducing waste!", 0, 0, 0, 0, "/static/arti/artimg10.gif"],
        "Crystal Recharger": ["Advances in storage minimises decay!", 0, 0, 0, 0, "/static/arti/artimg20.png"],
        "Ironside Effect": ["The resting site of a great viking encourages pillaging!", 0, 0, 0, 1, "/static/arti/artimg17.gif"],
        "Scroll of the Necromancer": ["Traps the souls of the dead, raising a great army!", 10000, 0, 0, 0, "/static/arti/artimg22.gif"],
    }

    arti_planets = random.sample(list(planets), len(arti_list))

    for i, (key, val) in enumerate(arti_list.items()):
        arti = Artefacts.objects.create(name=key,
                                       description=val[0],
                                       effect1=val[1],
                                       effect2=val[2],
                                       effect3=val[3],
                                       ticks_left=val[4],
                                       on_planet=arti_planets[i],
                                       image=val[5])
        arti_planets[i].artefact = arti
        arti_planets[i].save()


    print(arti_planets)
    print("Generating artefacts took " + str(time.time() - start_t) + "seconds")
    
def bonuses():
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
    
def settings():
    start_t = time.time()
    exclude_list = ['1','3','4','5','6','7','2']
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
    
def systems():
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