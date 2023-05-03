from .models import *
import numpy as np
import miniball
from collections import defaultdict
from .map_settings import *
from app.botops import *
from .specops import perform_operation, perform_incantation
from datetime import datetime
from datetime import timedelta
from django.template import RequestContext
from .helper_classes import *
from .calculations import *

def unitbuild(unit_list_dict, status):
    for unit, num in unit_list_dict.items():
        if num >=1:
            mult, _ = unit_cost_multiplier(status.research_percent_construction, status.research_percent_tech,
                                               unit_info[unit]['required_tech'])
            total_resource_cost = [int(np.ceil(x * mult)) for x in unit_info[unit]['cost']]

            for j in range(4):  # multiply all resources except time by number of units
                total_resource_cost[j] *= num

            total_resource_cost = ResourceSet(total_resource_cost)  # convert to more usable object
            if not total_resource_cost.is_enough(status):
                continue
                # Deduct resources
            status.energy -= total_resource_cost.ene
            status.minerals -= total_resource_cost.min
            status.crystals -= total_resource_cost.cry
            status.ectrolium -= total_resource_cost.ect

                # Create new construction job
            UnitConstruction.objects.create(user=status.user,
                                                n=num,
                                                unit_type=unit,
                                                ticks_remaining=total_resource_cost.time,
                                                energy_cost=total_resource_cost.ene,
                                                mineral_cost=total_resource_cost.min,
                                                crystal_cost=total_resource_cost.cry,
                                                ectrolium_cost=total_resource_cost.ect
                                                )  # calculated ticks
            status.save()  # update user's resources
        
def sendexpo(status, planet):
    fleet1 = Fleet.objects.get(owner=status.id, main_fleet=True)
    if fleet1.exploration >= 1:
        planet.owner = status.user
        planet.save()
        if planet.artefact is not None:
            planet.artefact.empire_holding = status.empire
            planet.artefact.save()
        expo_ship_nr = Fleet.objects.filter(owner = status.user, main_fleet = False, exploration = 1).count()
        pl_number = Planet.objects.filter(owner = status.user).count()
        calc_cost = pl_number + expo_ship_nr + 40 >> 2
        print(str(status) + ", " + str(calc_cost))
        status.fleet_readiness -= int(calc_cost)
        status.save()
        fleet1.exploration -= 1
        fleet1.save()
        scout = Scouting.objects.filter(user=status.id, planet=planet).first()
        if scout is None:
            Scouting.objects.create(user= User.objects.get(id=status.id),
                            planet = planet,
                            scout = 1.0)
        else:
            scout.scout = 1.0
            scout.save

def buildbuildings(planet, status, num_planets, total_ob, building_list_dict):
    for building, num in building_list_dict.items():
            # calc_building_cost was designed to give the View what it needed, so pull out just the values and multiply by num
        total_resource_cost, penalty = building.calc_cost(num, status.research_percent_construction,
                                                              status.research_percent_tech, status)


        total_resource_cost = ResourceSet(total_resource_cost)  # convert to more usable object
        ob_factor = calc_overbuild_multi(planet.size,
                                             planet.total_buildings + planet.buildings_under_construction, num)
        total_resource_cost.apply_overbuild(
                ob_factor)  # can't just use planet.overbuilt, need to take into account how many buildings we are making
            
        if not total_resource_cost.is_enough(status):
            continue


            # Deduct resources
        status.energy -= total_resource_cost.ene
        status.minerals -= total_resource_cost.min
        status.crystals -= total_resource_cost.cry
        status.ectrolium -= total_resource_cost.ect

        ticks = total_resource_cost.time  # calculated ticks

        if num > 0:
            Construction.objects.create(user=status.user,
                                        planet=planet,
                                        n=num,
                                        building_type=building.short_label,
                                        ticks_remaining=ticks)
            planet.buildings_under_construction += num

    planet.overbuilt = calc_overbuild(planet.size, planet.total_buildings + planet.buildings_under_construction)
    planet.overbuilt_percent = (planet.overbuilt - 1.0) * 100
    planet.save()
    status.save()
    
def manti(status, declared):
    spell = None
    if status.research_percent_culture >= 120:
        for _ in range(2):
            if declared == status.empire:
                spell = "Phantoms"
            else:
                spell = "Grow Planet's Size"
            perform_spell(spell, status) 
def foos(status, declared):
    spell = None
    if declared == status.empire:
        for _ in range(4):
            spell = "Dark Web"
            perform_spell(spell, status)
    else:
        if status.crystal_decay >= status.crystal_income:
            spell = "Incandescence"
        elif status.research_percent_culture >= 120:
            spell = "Enlightenment"
        perform_spell(spell, status)
def hks(status, declared):
    spell = None
    if status.crystal_decay >= status.crystal_income:
        spell = "Incandescence"

    elif status.research_percent_culture >= 70:
        spell = "War Illusions"
    perform_spell(spell, status)
def drw(status, declared):
    spell = None
    if status.crystal_decay >= status.crystal_income:
        spell = "Incandescence"
        perform_spell(spell, status)

    else:
        if declared == status.empire and status.research_percent_culture >= 120:
            if not Specops.objects.filter(user_from=status.user, name="War Illusions").exists():
                spell = "War Illusions"
                perform_spell(spell, status)
            else:
                for _ in range(2):
                    spell = "Phantoms"
                    perform_spell(spell, status)
        if declared != status.empire and status.research_percent_culture >= 120:
            if Specops.objects.filter(user_from=status.user, name="Enlightenment").exists():
                for _ in range(2):
                    spell = "Grow Planet's Size"
                    perform_spell(spell, status)
            else:                
                spell = "Enlightenment"
                perform_spell(spell, status)
        
def wooks(status, declared):
    spell = None
    if declared == status.empire and status.research_percent_culture >= 70 and not Specops.objects.filter(user_from=status.user, name="War Illusions").exists():
        spell = "War Illusions"
    elif status.research_percent_culture >= 120:
        spell = "Grow Planet's Size"
    perform_spell(spell, status) 

#def expbonus(status, unexp):
#    bcount = 0
#    bunexp =[p.id for p in Planet.objects.filter(owner=None).exclude(home_planet=True).order_by('-size') if Scouting.objects.filter(user=status.id, planet=p.id, scout__gte=1.0).exists()]
#    for p in bunexp:
#        p = Planet.objects.get(id=p)
#        if p.bonus_solar >= 1 and ((p.bonus_solar/100) + 1) * p.size >= 250:
#            planet = p
#            bcount += 1
#            break
#        if p.bonus_mineral >= 1 and ((p.bonus_mineral/100) + 1) * p.size >= 250:
#            planet = p
#            bcount += 1
#            break
#        if p.bonus_crystal >= 1 and ((p.bonus_crystal/100) + 1) * p.size >= 250:
#            planet = p
#            bcount += 1
#            break
#        if p.bonus_ectrolium >= 1 and ((p.bonus_ectrolium/100) + 1) * p.size >= 250:
#            planet = p
#            bcount += 1
#            break
#
#    if bcount >= 1:
#        sendexpo(status, planet)
#    else:
#        try:
#            p = unexp[0]
#            planet = Planet.objects.get(id=p)
#            sendexpo(status, planet)
#        except:
#            one = 1
    
def explore(status):            
    countunex = 0
    arti = [p.id for p in Planet.objects.filter(owner=None).exclude(artefact=None) if Scouting.objects.filter(user=status.id, planet=p.id, scout__gte=1.0).exists()]
    unexp =[p.id for p in Planet.objects.filter(owner=None).exclude(home_planet=True).exclude(size__lt=200).order_by('-size') if Scouting.objects.filter(user=status.id, planet=p.id, scout__gte=1.0).exists()]
                
    if arti and status.fleet_readiness >= 50:
        for p in arti:
            planet = Planet.objects.get(id=p)
            sendexpo(status, planet)
        
    for i in range(5):
        if status.fleet_readiness >= 50:
            try:
                p = unexp[i-1]
                planet = Planet.objects.get(id=p)
                sendexpo(status, planet)
            except:
                break
        else:
            break
    
