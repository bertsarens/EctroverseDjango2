from django.db.models import Q, Sum
from .models import *
from app.constants import *
from app.helper_functions import generate_fleet_order, find_nearest_portal, join_main_fleet
import numpy as np
from app.models import *
from datetime import datetime
import copy
import math


def battleReadinessLoss(status, user2, planet):
    # print(, user2)
    fa = (1 + status.num_planets) / (1 + user2.num_planets)
    empire1 = status.empire
    empire2 = user2.empire
    high = 100

    if (empire1 == empire2):  # intra-fam attack
        fa = pow(fa, 1.3)
        fb = 1.0
        high = 16.0
    else:
        fa = pow(fa, 1.3);
        fb = (1 + empire1.planets) / (1 + empire2.planets)
        fb = pow(fb, 1.8)

    fdiv = 0.5
    if fb < fa:
        fdiv = 0.5 * pow(fb / fa, 0.8)
    fa = (fdiv * fa) + ((1.0 - fdiv) * fb)
    if fa < 0.50:
        fa = 0.50
    fa *= 11.5

    war = False
    ally = False
    nap = False

    relations_from_empire = Relations.objects.filter(empire1=empire1)
    relations_to_empire = Relations.objects.filter(empire2=empire2)

    for rel in relations_from_empire:
        if rel.relation_type == 'W' and rel.empire2 == empire2:
            war = True
        if rel.relation_type == 'A' and rel.empire2 == empire2:
            ally = True
        if rel.relation_type == 'NC' or rel.relation_type == 'PC' or rel.relation_type == 'N' and rel.empire2 == empire2:
            nap = True

    for rel in relations_to_empire:
        if rel.relation_type == 'W' and rel.empire2 == empire1:
            war = True
        if rel.relation_type == 'A' and rel.empire2 == empire1:
            ally = True
        if rel.relation_type == 'NC' or rel.relation_type == 'PC' or rel.relation_type == 'N' and rel.empire2 == empire1:
            nap = True

    if empire1.id == empire2.id or ally or war:
        fa /= 3

    if Specops.objects.filter(name="Planetary Beacon", planet=planet).exists():
        fa = 1
    else:
        spec_ops = Specops.objects.filter(user_to=user2.user, name="Dark Web")
        for specop in spec_ops:
            fa *= 1 + specop.specop_strength / 100

    if Specops.objects.filter(user_to=user2.user, name="Enlightenment", extra_effect="BadFR").exists():
        en = Specops.objects.get(user_to=user2.user, name="Enlightenment", extra_effect="BadFR")
        fa /= (1 + en.specop_strength / 100)

    if nap:
        fa = max(50, fa)

    # add personal and fam news
    # dont forget to delete anempty fleet!
    # deparate losses for main fleet and stationed! grr

    return min(round(fa), high)

def calc_lost_units_attacker(attacking_fleet, attacker_losses):
    if attacker_losses["Carriers"]:
        units_lost = calc_lost_units_in_carriers(attacking_fleet, attacker_losses["Carriers"])
    else:
        units_lost = calc_lost_units_in_transports(attacking_fleet, attacker_losses["Transports"])
    
    attacker_losses["Bombers"] += units_lost["Bombers"]
    attacker_losses["Fighters"] += units_lost["Fighters"]
    attacker_losses["Transports"] += units_lost["Transports"]
    attacker_losses["Goliaths"] += units_lost["Goliaths"]
    attacker_losses["Droids"] += units_lost["Droids"]
    attacker_losses["Soldiers"] += units_lost["Soldiers"]

    attacking_fleet.carrier -= attacker_losses["Carriers"]
    attacking_fleet.cruiser -= attacker_losses["Cruisers"]
    attacking_fleet.phantom -= attacker_losses["Phantoms"]
    attacking_fleet.bomber -= attacker_losses["Bombers"]
    attacking_fleet.fighter -= attacker_losses["Fighters"]
    attacking_fleet.transport -= attacker_losses["Transports"]
    attacking_fleet.goliath -= attacker_losses["Goliaths"]
    attacking_fleet.droid -= attacker_losses["Droids"]
    attacking_fleet.soldier -= attacker_losses["Soldiers"]
    
    attacking_fleet.save()


def calc_lost_units_in_carriers(attacking_fleet, carrier_losses):
    # calc lost bombers, transports and fighters
    lost_units = {"Bombers":0, "Fighters":0, "Transports":0, "Goliaths":0, "Droids":0, "Soldiers":0}
    if attacking_fleet.carrier:
        fraction_carriers_lost = carrier_losses / attacking_fleet.carrier
        lost_units["Bombers"] = round(attacking_fleet.bomber * fraction_carriers_lost)
        lost_units["Fighters"] = round(attacking_fleet.fighter * fraction_carriers_lost)
        lost_units["Transports"] = round(attacking_fleet.transport * fraction_carriers_lost)

        lost_units_transports = calc_lost_units_in_transports(attacking_fleet, lost_units["Transports"])
        lost_units["Goliaths"] = lost_units_transports["Goliaths"]
        lost_units["Droids"] = lost_units_transports["Droids"]
        lost_units["Soldiers"] = lost_units_transports["Soldiers"]

    return lost_units

def calc_lost_units_in_transports(attacking_fleet, transports_losses):
    # calc lost goliahs, droids and soldiers
    lost_units = {"Bombers":0, "Fighters":0, "Transports":0, "Goliaths":0, "Droids":0, "Soldiers":0}
    if attacking_fleet.transport:
        fraction_transports_lost = transports_losses / attacking_fleet.transport
        lost_units["Goliaths"] = round(attacking_fleet.goliath * fraction_transports_lost)
        lost_units["Droids"] = round(attacking_fleet.droid * fraction_transports_lost)
        lost_units["Soldiers"] = round(attacking_fleet.soldier * fraction_transports_lost)

    return lost_units

def defenders_fleet_update(defender, defending_fleets, attacked_planet):
    main_fleet = Fleet.objects.get(owner=defender.id, main_fleet=True)
    stationed_fleet = Fleet.objects.filter(owner=defender.id, on_planet=True,\
                                        x=attacked_planet.x, y=attacked_planet.y, i=attacked_planet.i).first()
    if stationed_fleet:
        # stationed fleet can only be 1, since it will all merge on that planet
        #bombers
        mf = main_fleet.bomber / max(main_fleet.bomber + stationed_fleet.bomber,1)
        mf_loss = math.ceil(defending_fleets["bomber"] * mf)
        main_fleet.bomber -= mf_loss
        stationed_fleet.bomber -= (defending_fleets["bomber"] - mf_loss)
        #fighters
        mf = main_fleet.fighter / max(main_fleet.fighter + stationed_fleet.fighter,1)
        mf_loss = math.ceil(defending_fleets["fighter"] * mf)
        main_fleet.fighter -= mf_loss
        stationed_fleet.fighter -= (defending_fleets["fighter"] - mf_loss)
        #transports
        mf = main_fleet.transport / max(main_fleet.transport + stationed_fleet.transport,1)
        mf_loss = math.ceil(defending_fleets["transport"] * mf)
        main_fleet.transport -= mf_loss
        stationed_fleet.transport -= (defending_fleets["transport"] - mf_loss)
        #cruisers
        mf = main_fleet.cruiser / max(main_fleet.cruiser + stationed_fleet.cruiser,1)
        mf_loss = math.ceil(defending_fleets["cruiser"] * mf)
        main_fleet.cruiser -= mf_loss
        stationed_fleet.cruiser -= (defending_fleets["cruiser"] - mf_loss)
        #carriers
        mf = main_fleet.carrier / max(main_fleet.carrier + stationed_fleet.carrier,1)
        mf_loss = math.ceil(defending_fleets["carrier"] * mf)
        main_fleet.carrier -= mf_loss
        stationed_fleet.carrier -= (defending_fleets["carrier"] - mf_loss)
        # soldiers
        mf = main_fleet.soldier / max(main_fleet.soldier + stationed_fleet.soldier,1)
        mf_loss = math.ceil(defending_fleets["soldier"] * mf)
        main_fleet.soldier -= mf_loss
        stationed_fleet.soldier -= (defending_fleets["soldier"] - mf_loss)
        # droids
        mf = main_fleet.droid / max(main_fleet.droid + stationed_fleet.droid,1)
        mf_loss = math.ceil(defending_fleets["droid"] * mf)
        main_fleet.droid -= mf_loss
        stationed_fleet.droid -= (defending_fleets["droid"] - mf_loss)
        # goliaths
        mf = main_fleet.goliath / max(main_fleet.goliath + stationed_fleet.goliath,1)
        mf_loss = math.ceil(defending_fleets["goliath"] * mf)
        main_fleet.goliath -= mf_loss
        stationed_fleet.goliath -= (defending_fleets["goliath"] - mf_loss)
        # phantoms
        mf = main_fleet.phantom / max(main_fleet.phantom + stationed_fleet.phantom,1)
        mf_loss = math.ceil(defending_fleets["phantom"] * mf)
        main_fleet.phantom -= mf_loss
        stationed_fleet.phantom -= (defending_fleets["phantom"] - mf_loss)
        stationed_fleet.save()
    else:
        main_fleet.bomber = defending_fleets["bomber"]
        main_fleet.fighter = defending_fleets["fighter"]
        main_fleet.transport = defending_fleets["transport"]
        main_fleet.cruiser = defending_fleets["cruiser"]
        main_fleet.carrier = defending_fleets["carrier"]
        main_fleet.soldier = defending_fleets["soldier"]
        main_fleet.droid = defending_fleets["droid"]
        main_fleet.goliath = defending_fleets["goliath"]
        main_fleet.phantom = defending_fleets["phantom"]

    main_fleet.save()

def calcfleet(status, attacked_planet, attacker, defender):
    inc = status.energy_production * 0.5
    if status.population_upkeep_reduction >= inc:
        inc = status.population_upkeep_reduction
    if status.id == 6:
        inc = status.energy_production - (status.buildings_upkeep + status.portals_upkeep)
        bomber = round((inc* 0.025) / 2)
        fighter = round((inc * 0.055) / 1.6)
        transport = round((inc * 0.01) / 3.2)
        cruiser = round((inc * 0.3) / 12)
        carrier = round((inc * 0.05) / 18)
        soldier = round((inc * 0.08) / 0.4)
        droid = round((inc * 0.08) / 0.6)
        goliath = round((inc * 0.04) / 2.8)
    else:
        bomber = round((inc* 0.025) / 2)
        fighter = round((inc * 0.055) / 1.6)
        transport = round((inc * 0.01) / 3.2)
        cruiser = round((inc * 0.44) / 12)
        carrier = round((inc * 0.05) / 18)
        soldier = round((inc * 0.08) / 0.4)
        droid = round((inc * 0.08) / 0.6)
        goliath = round((inc * 0.04) / 2.8)
    
    totunits = Fleet.objects.get(owner=status.id, main_fleet=True)
    attack = 0
    curr_units_bomber = totunits.bomber
    if curr_units_bomber >= bomber * 0.7:
        attack += 1   
    curr_units_fighter = totunits.fighter
    if curr_units_fighter >= fighter * 0.7:
        attack += 1
    curr_units_transport  = totunits.transport
    if curr_units_transport >= transport * 0.7:
        attack += 1
    curr_units_cruiser  = totunits.cruiser
    if curr_units_cruiser >= cruiser * 0.9:
        attack += 1
    curr_units_carrier  = totunits.carrier
    if curr_units_carrier >= carrier * 0.7:
        attack += 1
    curr_units_soldier  = totunits.soldier
    if curr_units_soldier >= soldier * 0.7:
        attack += 1
    curr_units_droid  = totunits.droid
    if curr_units_droid >= droid * 0.7:
        attack += 1
    curr_units_goliath  = totunits.goliath
    if curr_units_goliath >= goliath * 0.7:
        attack += 1
    print(str(status.user_name) + ": " + str(attack))
    if attack == 8:
        attack_planet(status, attacked_planet, attacker, defender)
    
def generate_news(battle_report, attacker, defender, attacked_planet):
    # SA = 'SA', _('Successfull Attack')
    # UA = 'UA', _('Unsuccessfull Attack')
    # SD = 'SD', _('Successfull Defence')
    # UD = 'UD', _('Unsuccessfull Defence')

    news_type_attacker = "SA" if battle_report["won"] == "A" else "UA"
    news_type_defender = "SD" if battle_report["won"] == "D" else "UD"

    ironside = Artefacts.objects.get(name="Ironside Effect")
    resources = ["Energy", "Mineral", "Crystal", "Ectrolium"]
    
    attack_news_msg = {"Bombers":0,
                            "Fighters": 0,
                            "Transports": 0,
                            "Cruisers": 0,
                            "Carriers": 0,
                            "Soldiers": 0,
                            "Droids": 0,
                            "Goliaths": 0,
                            "Phantoms": 0,
                            "Necromancers":0}
    
    attack_msg = ""
    
    if battle_report["p1"]["phase"]:
        for unit, losses in battle_report["p1"]["att_loss"].items():
            if losses > 0:
                attack_news_msg[unit] += losses
            

    if battle_report["p2"]["phase"]:
        for unit, losses in battle_report["p2"]["att_loss"].items():
            if losses > 0:
                attack_news_msg[unit] += losses

    if battle_report["p3"]["phase"]:
        for unit, losses in battle_report["p3"]["att_loss"].items():
            if losses > 0:
                attack_news_msg[unit] += losses

    if battle_report["p4"]["phase"]:
        for unit, losses in battle_report["p4"]["att_loss"].items():
            if losses > 0:
                attack_news_msg[unit] += losses
                
    for unit, losses in attack_news_msg.items():
        if losses > 0:
            attack_msg += str(unit) + ": " + str(losses) + ", "
    
    
    defender_msg = ""
    defender_fleet_msg = {"Bombers":0,
                            "Fighters": 0,
                            "Transports": 0,
                            "Cruisers": 0,
                            "Carriers": 0,
                            "Soldiers": 0,
                            "Droids": 0,
                            "Goliaths": 0,
                            "Phantoms": 0,
                            "Planet population": 0,
                            "Necromancers":0}

    if battle_report["p1"]["phase"]:
        for unit, losses in battle_report["p1"]["def_loss"].items():
            if losses > 0:
                defender_fleet_msg[unit] += losses

    if battle_report["p2"]["phase"]:
        for unit, losses in battle_report["p2"]["def_loss"].items():
            if losses > 0:
                defender_fleet_msg[unit] += losses

    if battle_report["p3"]["phase"]:
        for unit, losses in battle_report["p3"]["def_loss"].items():
            if losses > 0:
                defender_fleet_msg[unit] += losses

    if battle_report["p4"]["phase"]:
        for unit, losses in battle_report["p4"]["def_loss"].items():
            if losses > 0 and unit not in resources:
                defender_fleet_msg[unit] += losses
    
    for unit, losses in defender_fleet_msg.items():
        if losses > 0 and unit not in resources:
            defender_msg += str(unit) + ": " + str(losses) + ", "
                

    
    if battle_report["p1"]["phase"] and battle_report["p1"]["att_flee"]:
        attack_msg += "\nAttackers fleet was overwhelmed in stage 1 ."
        defender_msg += "\nDefending forces prevailed in stage 1! "
    if battle_report["p1"]["phase"] and battle_report["p1"]["def_flee"]:
        attack_msg += "\nAttackers overpowered the enemy in stage 1!. "
        defender_msg += "\nDefending forces preferred not to directly engage in stage 1! "
    if battle_report["p2"]["phase"] and battle_report["p2"]["att_flee"]:
        attack_msg += "\nAttackers fleet was overwhelmed in stage 2. "
        defender_msg += "\nDefending forces prevailed in stage 2! "
    if battle_report["p2"]["phase"] and battle_report["p2"]["def_flee"]:
        attack_msg += "\nAttackers overpowered the enemy in stage 2!. "
        defender_msg += "\nDefending forces preferred not to directly engage in stage 2! "
    if battle_report["p3"]["phase"] and battle_report["p3"]["att_flee"]:
        attack_msg += "\nAttackers fleet was overwhelmed in stage 3. "
        defender_msg += "\nDefending forces prevailed in stage 3! "
    if battle_report["p3"]["phase"] and battle_report["p3"]["def_flee"]:
        attack_msg += "\nAttackers overpowered the enemy in stage 3!. "
        defender_msg += "\nDefending forces preferred not to directly engage in stage 3! "
    if battle_report["p4"]["phase"] and battle_report["p4"]["att_flee"]:
        attack_msg += "\nAttackers fleet was overwhelmed in stage 4. "
        defender_msg += "\nDefending forces prevailed in stage 4! "        
    if battle_report["p4"]["phase"] and battle_report["p4"]["def_flee"]:
        attack_msg += "\nAttackers overpowered the enemy in stage 4!. "
        defender_msg += "\nDefending forces preferred not to directly engage in stage 4! \n"

    if ironside.empire_holding == attacker.empire:
        for unit, losses in battle_report["p4"]["def_loss"].items():
            if losses > 0 and unit in resources:
                defender_msg += str(losses) + " " + str(unit) + " "
        defender_msg += "was stolen!"

    News.objects.create(user1=User.objects.get(id=attacker.id),
                        user2=User.objects.get(id=defender.id),
                        empire1=attacker.empire,
                        empire2=defender.empire,
                        fleet1=attack_msg,
                        fleet2=defender_msg,
                        news_type=news_type_attacker,
                        date_and_time=datetime.now(),
                        planet=attacked_planet,
                        is_personal_news=True,
                        is_empire_news=True,
                        tick_number=RoundStatus.objects.get().tick_number
                        )

    News.objects.create(user1=User.objects.get(id=defender.id),
                        user2=User.objects.get(id=attacker.id),
                        empire1=defender.empire,
                        empire2=attacker.empire,
                        fleet1=defender_msg,
                        fleet2=attack_msg,
                        news_type=news_type_defender,
                        date_and_time=datetime.now(),
                        planet=attacked_planet,
                        is_personal_news=True,
                        is_empire_news=True,
                        tick_number=RoundStatus.objects.get().tick_number
                        )


def attack_planet(status, attacked_planet, attacker, defender):
    attacking_fleet = Fleet.objects.get(owner=status.id, main_fleet=True) 
    main_defender_fleet = Fleet.objects.get(owner=defender.id, main_fleet=True)
    stationed_defender_fleet = Fleet.objects.filter(owner=defender.id, on_planet=True,\
                                        x=attacked_planet.x, y=attacked_planet.y, i=attacked_planet.i).first()
    defending_fleets = {"bomber":0,
                            "fighter": 0,
                            "transport": 0,
                            "cruiser": 0,
                            "carrier": 0,
                            "soldier": 0,
                            "droid": 0,
                            "goliath": 0,
                            "phantom": 0,
                            "wizard": 0,
                            "agent": 0,
                            "ghost": 0,
                            "exploration": 0
                            }
        # portal coverage
    if stationed_defender_fleet:
        for key in defending_fleets.keys():
            defending_fleets[key] = main_defender_fleet.__dict__[key] + \
                                    stationed_defender_fleet.__dict__[key]
    else:
        for key in defending_fleets.keys():
                defending_fleets[key] = main_defender_fleet.__dict__[key] 

    attstats = {}
    defstats = {}
    battle_report = {}
    for i in range(0, len(unit_labels)):
        attstats[unit_labels[i]] = copy.deepcopy(unit_stats[i])
        unit_bonus = race_info_list[attacker.get_race_display()].get(unit_race_bonus_labels[i], 1.0)
        for j in range(0, 4):
            attstats[unit_labels[i]][j] = round(attstats[unit_labels[i]][j] * unit_bonus, 2)
        defstats[unit_labels[i]] = copy.deepcopy(unit_stats[i])
        unit_bonus = race_info_list[defender.get_race_display()].get(unit_race_bonus_labels[i], 1.0)
        for j in range(0, 4):
            defstats[unit_labels[i]][j] = round(defstats[unit_labels[i]][j] * unit_bonus, 2)

    battle_report["tired_forces"] = ""
    battle_report["won"] = "C"
    battle_report["p1"] = {}
    battle_report["p2"] = {}
    battle_report["p3"] = {}
    battle_report["p4"] = {}

    battle_report["p1"]["phase"] = False
    battle_report["p2"]["phase"] = False
    battle_report["p3"]["phase"] = False
    battle_report["p4"]["phase"] = False



    # battle_report += "\n\n defending_fleets2" + str(defending_fleets)
    battle_report["fleet_readiness"] = attacker.fleet_readiness
    if attacker.fleet_readiness < -100:
        return battle_report

    defender.military_flag = 1
    defender.save()

    fa = 1
    if attacker.fleet_readiness < 0:
        fa = 1.0 - attacker.fleet_readiness / 130.0

    attfactor = race_info_list[attacker.get_race_display()].get("military_attack", 1.0) / \
                race_info_list[defender.get_race_display()].get("military_defence", 1.0) * fa
    deffactor = race_info_list[defender.get_race_display()].get("military_attack", 1.0) / \
                race_info_list[attacker.get_race_display()].get("military_defence", 1.0) / fa
    deffactor = deffactor * (attacked_planet.protection / 100)
    attacker.fleet_readiness -= battleReadinessLoss(attacker, defender, attacked_planet)
    attacker.save()

    if Specops.objects.filter(name="Planetary Beacon", planet=attacked_planet).exists():
        attfactor /= 1.1
        deffactor *= 1.1
    
    if Specops.objects.filter(name="War Illusions", user_to=attacker.user).exists():
        attackillusions= Specops.objects.get(name="War Illusions", user_to=attacker.user)
        attfactor *= 1 + (attackillusions.specop_strength/100)
    
    if Specops.objects.filter(name="War Illusions", user_to=defender.user).exists():
        defenceillusions= Specops.objects.get(name="War Illusions", user_to=defender.user)
        deffactor *= 1 + (defenceillusions.specop_strength/100)
    
    # defsatsbase = defsats = attacked_planet.defense_sats
    hpshield = 0
    for sh in Specops.objects.filter(user_to=defender.user, name='Planetary Shielding', planet=attacked_planet):
    	strength = sh.specop_strength
    	hpshield += strength
    shields = (shield_absorb * attacked_planet.shield_networks) + hpshield

    # phase1
    attacker_flee, defender_flee, \
    att_loss, def_loss = phase1(attacking_fleet, defending_fleets, attstats,
                                defstats, attfactor, deffactor, attacked_planet, attacker, defender, shields)
    battle_report["p1"]["phase"] = True
    battle_report["p1"]["att_flee"] = attacker_flee
    battle_report["p1"]["def_flee"] = defender_flee
    battle_report["p1"]["att_loss"] = att_loss
    battle_report["p1"]["def_loss"] = def_loss

    if attacker_flee:
        defenders_fleet_update(defender, defending_fleets, attacked_planet)
        battle_report["won"] = "D"
        generate_news(battle_report, attacker, defender, attacked_planet)
        botattack.objects.create(user1=status.user, user2 = attacked_planet.owner.userstatus.user_name, at_type="Attack", time="260")
        return battle_report
        
        
    # phase2
    attacker_flee, defender_flee, \
    att_loss, def_loss = phase2(attacking_fleet, defending_fleets, attstats,
                                defstats, attfactor, deffactor, attacked_planet, attacker, defender, shields)
    battle_report["p2"]["phase"] = True
    battle_report["p2"]["att_flee"] = attacker_flee
    battle_report["p2"]["def_flee"] = defender_flee
    battle_report["p2"]["att_loss"] = att_loss
    battle_report["p2"]["def_loss"] = def_loss

    if attacker_flee:
        defenders_fleet_update(defender, defending_fleets, attacked_planet)
        battle_report["won"] = "D"
        generate_news(battle_report, attacker, defender, attacked_planet)
        botattack.objects.create(user1=status.user, user2 = attacked_planet.owner.userstatus.user_name, at_type="Attack", time="15")
        return battle_report
        
    # phase3
    attacker_flee, defender_flee, \
    att_loss, def_loss = phase3(attacking_fleet, defending_fleets, attstats,
                                defstats, attfactor, deffactor, attacked_planet, attacker, defender, shields)
    battle_report["p3"]["phase"] = True
    battle_report["p3"]["att_flee"] = attacker_flee
    battle_report["p3"]["def_flee"] = defender_flee
    battle_report["p3"]["att_loss"] = att_loss
    battle_report["p3"]["def_loss"] = def_loss

    if attacker_flee:
        defenders_fleet_update(defender, defending_fleets, attacked_planet)
        battle_report["won"] = "D"
        generate_news(battle_report, attacker, defender, attacked_planet)
        botattack.objects.create(user1=status.user, user2 = attacked_planet.owner.userstatus.user_name, at_type="Attack", time="15")
        return battle_report
        
    # phase4
    attacker_flee, defender_flee, \
    att_loss, def_loss = phase4(attacking_fleet, defending_fleets, attstats,
                                defstats, attfactor, deffactor, attacked_planet, attacker, defender, shields)
    battle_report["p4"]["phase"] = True
    battle_report["p4"]["att_flee"] = attacker_flee
    battle_report["p4"]["def_flee"] = defender_flee
    battle_report["p4"]["att_loss"] = att_loss
    battle_report["p4"]["def_loss"] = def_loss

    # spread losses among main fleet and stationed for the defender
    defenders_fleet_update(defender, defending_fleets, attacked_planet)

    if attacker_flee:
        battle_report["won"] = "D"
        generate_news(battle_report, attacker, defender, attacked_planet)
        botattack.objects.create(user1=status.user, user2 = attacked_planet.owner.userstatus.user_name, at_type="Attack", time="15")
        return battle_report

    if defender_flee:
        battle_report["won"] = "A"
        attacked_planet.owner = status.user
        attacked_planet.save()
        attacker_size = int(attacker.num_planets)
        defender_size = int(defender.num_planets)
        if attacked_planet.artefact is not None:
            attacked_planet.artefact.empire_holding = attacker.empire
            attacked_planet.artefact.save()
        if defender_size / attacker_size > 0.6:
            attacked_planet.solar_collectors *= 0.9
            attacked_planet.fission_reactors *= 0.9
            attacked_planet.mineral_plants *= 0.9
            attacked_planet.crystal_labs *= 0.9
            attacked_planet.refinement_stations *= 0.9
            attacked_planet.cities *= 0.9
            attacked_planet.research_centers *= 0.9
            attacked_planet.defense_sats *= 0.9
            attacked_planet.shield_networks *= 0.9
            attacked_planet.total_buildings = 0            
        else:
            attacked_planet.solar_collectors = 0
            attacked_planet.fission_reactors = 0
            attacked_planet.mineral_plants = 0
            attacked_planet.crystal_labs = 0
            attacked_planet.refinement_stations = 0
            attacked_planet.cities = 0
            attacked_planet.research_centers = 0
            attacked_planet.defense_sats = 0
            attacked_planet.shield_networks = 0
            attacked_planet.total_buildings = 0
        attacked_planet.portal = False
        attacked_planet.buildings_under_construction = 0
        attacked_planet.protection = 0
        attacked_planet.save()
        for con in Construction.objects.all():
            if con.planet == attacked_planet:
                con.delete()
        scouting = Scouting.objects.filter(user=status.user, planet=attacked_planet).first()
        if scouting is None:
            Scouting.objects.create(user= User.objects.get(id=attacker.id),
                                planet = attacked_planet,
                                scout = '1')
        else:
            scouting.scout = 1.0
            scouting.save
        
        generate_news(battle_report, attacker, defender, attacked_planet)
        return battle_report


####################
#      PHASE 1     #
####################
def phase1(attacking_fleet,
           defending_fleets,
           attstats, defstats,
           attfactor,
           deffactor,
           attacked_planet,
           attacker,
           defender,
           shields):
    attacker_flee = False
    defender_flee = False

    # ========= Calculate damage factors =========#
    attdam = attacking_fleet.cruiser * attstats["Cruisers"][0] + \
             attacking_fleet.phantom * attstats["Phantoms"][0]
    
    necro = Artefacts.objects.get(name="Scroll of the Necromancer")
    if necro.empire_holding == attacker.empire:
        attdam += necro.effect1 * 1
    
    defdam = defending_fleets["cruiser"] * defstats["Cruisers"][0] + \
             defending_fleets["phantom"] * defstats["Phantoms"][0] + \
             sats_attack * attacked_planet.defense_sats 
    
    if necro.empire_holding == defender.empire:
        defdam += necro.effect1 * 1
    
    if Specops.objects.filter(user_to=attacker.user, name="War Illusions").exists():
        spec_ops = Specops.objects.filter(user_to=attacker.user, name="War Illusions")
        for specop in spec_ops:
            attfactor *= 1 + (specop.specop_strength / 100)


    if Specops.objects.filter(user_to=defender.user, name="War Illusions").exists():
        spec_ops = Specops.objects.filter(user_to=defender.user, name="War Illusions")
        for specop in spec_ops:
            deffactor *= 1 + (specop.specop_strength / 100)

        
    attdam = attdam * attfactor * ((1.0 + 0.005 * attacker.research_percent_military)/(1.0 + 0.005 * defender.research_percent_military))

    defdam = defdam * deffactor * ((1.0 + 0.005 * defender.research_percent_military)/(1.0 + 0.005 * attacker.research_percent_military))
    if attdam >= 1.0:
        attdam -= attdam * (1.0 - pow(2.5, -(shields / attdam)))

    # ========= Determine if anyone will flee =========#

    # damage is too high defender flee
    if (defdam < 1.0) or ((attdam / defdam) * 10.0 >= defender.long_range_attack_percent):
        defender_flee = True
        return attacker_flee, defender_flee, {}, {}
    # defender flees, if settings are 100% this means attacker deals 10x more damage than defender
    if (attdam / defdam) * 100.0 >= defender.long_range_attack_percent:
        defdam *= 0.15
        attdam *= 0.10
        # results[3] |= 0x100;
    # attacker flees, same logic as above
    if (attdam >= 1.0) and ((defdam / attdam) * 100.0 >= defender.long_range_attack_percent):
        defdam *= 0.20
        attdam *= 0.10
        attacker_flee = True
    if attdam == 0:
        attacker_flee = True

    # ========= Damage to attacking fleets =========#
    hpcarrier = attacking_fleet.carrier * attstats["Carriers"][1]
    hpcruiser = attacking_fleet.cruiser * attstats["Cruisers"][1]
    hpphantom = attacking_fleet.phantom * attstats["Phantoms"][1]
    
    hpnecro = 0
    necro = Artefacts.objects.get(name="Scroll of the Necromancer")
    if necro.empire_holding == attacker.empire:
        hpnecro = necro.effect1 * 30
    
    hptotal = hpcarrier + hpcruiser + hpphantom + hpnecro
    
    damcarrier = 0
    damcruiser = 0
    damphantom = 0
    damnecro = 0

    # percentage of damage that wil be received by the unit
    if hptotal:
        damcarrier = hpcarrier / hptotal
        damcruiser = hpcruiser / hptotal
        damphantom = hpphantom / hptotal     
    
    if hpnecro >=1:
        damnecro = hpnecro / hptotal
    
    # calc attacking/defending cruiser ratio, transfer the damage from carriers to cruisers and phantoms
    fa = 0.0
    if defending_fleets["cruiser"] > 0:
        fa = attacking_fleet.cruiser / defending_fleets["cruiser"]
    damcarrier *= pow(1.50, -fa)

    fb = damcarrier + damcruiser + damphantom + damnecro

    if fb >= 0.00001:
        fa = defdam / fb
        damcarrier *= fa
        damcruiser *= fa
        damphantom *= fa
        damnecro += fa

    if damcarrier > hpcarrier:
        damcruiser += damcarrier - hpcarrier
    if damcruiser > hpcruiser:
        damphantom += damcruiser - hpcruiser
    if damphantom > hpphantom:
        damcruiser += damphantom - hpphantom
    if damnecro > hpnecro:
        damcarrier += damnecro - hpnecro
    
    neckilled = 0
    if necro.empire_holding == attacker.empire:
        neckilled = round(min(necro.effect1, damnecro * 100.0 / 30))
        necro.effect1 -= neckilled
        necro.save()
    
    attacker_losses = {"Bombers": 0, "Fighters": 0, "Transports": 0,
                       "Cruisers": round(min(attacking_fleet.cruiser, damcruiser / attstats["Cruisers"][1])),
                       "Carriers": round(min(attacking_fleet.carrier, damcarrier / attstats["Carriers"][1])),
                       "Soldiers": 0, "Droids": 0, "Goliaths": 0,
                       "Phantoms": round(min(attacking_fleet.phantom, damphantom / attstats["Phantoms"][1])),
                       "Necromancers": neckilled}

    calc_lost_units_attacker(attacking_fleet, attacker_losses)
    attacking_fleet.save()

    # ========= Damage to defending fleets =========#
    hpcruiser = defending_fleets["cruiser"] * defstats["Cruisers"][1]
    hpphantom = defending_fleets["phantom"] * defstats["Phantoms"][1]
    hpsats = attacked_planet.defense_sats * sats_defence
    
    hpnecro = 0
    if necro.empire_holding == defender.empire:
        hpnecro = necro.effect1 * 30 
    
    hptotal = hpcruiser + hpphantom + hpsats + hpnecro
    
    damcruiser = 0
    damphantom = 0
    damsats = 0
    damnecro = 0

    if hptotal:
        damcruiser = hpcruiser / hptotal
        damphantom = hpphantom / hptotal
        damsats = hpsats / hptotal
    
    if hpnecro >=1:
        damnecro = hpnecro / hptotal

    fa = 0.0
    if attacking_fleet.cruiser > 0:
        fa = defending_fleets["cruiser"] / attacking_fleet.cruiser
    damsats *= pow(2.80, -fa)

    fb = damcruiser + damphantom + damsats + damnecro

    if fb >= 0.00001:
        fa = attdam / fb
        damcruiser *= fa
        damphantom *= fa
        damsats *= fa
        damnecro *= fa

    if damcruiser > hpcruiser:
        damphantom += damcruiser - hpcruiser
    if damphantom > hpphantom:
        damsats += damphantom - hpphantom
    if damsats > hpsats:
        damcruiser += damsats - hpsats
    if damnecro > hpnecro:
        damphantom += damnecro - hpnecro
    
    neckilled = 0
    if necro.empire_holding == defender.empire:
        neckilled = round(min(necro.effect1, damnecro * 100.0 / 30))
        necro.effect1 -= neckilled
        necro.save()
    
    defender_losses = {"Bombers": 0, "Fighters": 0, "Transports": 0,
                       "Cruisers": round(min(defending_fleets["cruiser"], damcruiser / defstats["Cruisers"][1])),
                       "Carriers": 0, "Soldiers": 0, "Droids": 0, "Goliaths": 0,
                       "Phantoms": round(min(defending_fleets["phantom"], damphantom / defstats["Phantoms"][1])),
                       "Defence Satellites": round(min(attacked_planet.defense_sats, damsats / sats_defence)),
                       "Necromancers": neckilled}

    attacked_planet.defense_sats -= defender_losses["Defence Satellites"]
    attacked_planet.save()

    defending_fleets["cruiser"] -= defender_losses["Cruisers"]
    defending_fleets["phantom"] -= defender_losses["Phantoms"]

    return attacker_flee, defender_flee, attacker_losses, defender_losses


####################
#      PHASE 2     #
####################
def phase2(attacking_fleet,
           defending_fleets,
           attstats, defstats,
           attfactor,
           deffactor,
           attacked_planet,
           attacker,
           defender,
           shields):
    attacker_flee = False
    defender_flee = False

    # ========= Calculate damage factors =========#
    attdam = attacking_fleet.cruiser * attstats["Cruisers"][0] + \
             attacking_fleet.phantom * attstats["Phantoms"][0] + \
             attacking_fleet.fighter * attstats["Fighters"][0]
    
    necro = Artefacts.objects.get(name="Scroll of the Necromancer")
    if necro.empire_holding == attacker.empire:
        attdam += necro.effect1 * 1
    
    defdam = defending_fleets["cruiser"] * defstats["Cruisers"][0] + \
             defending_fleets["phantom"] * defstats["Phantoms"][0] + \
             defending_fleets["fighter"] * defstats["Fighters"][0] + \
             sats_attack * attacked_planet.defense_sats

    if necro.empire_holding == defender.empire:
        defdam += necro.effect1 * 1

    attdam = attdam * attfactor * ((1.0 + 0.005 * attacker.research_percent_military) / \
                                   (1.0 + 0.005 * defender.research_percent_military))

    defdam = defdam * deffactor * ((1.0 + 0.005 * defender.research_percent_military) / \
                                   (1.0 + 0.005 * attacker.research_percent_military))

    if attdam >= 1.0:
        attdam -= attdam * (1.0 - pow(2.5, -(shields / attdam)))

    # ========= Determine if anyone will flee =========#
    # damage is too high defender flee
    if (defdam < 1.0) or (attdam / defdam) * 10.0 >= defender.air_vs_air_percent:
        defender_flee = True
        return attacker_flee, defender_flee, {}, {}
    # defender flees, if settings are 100% this means attacker deals 10x more damage than defender
    if (attdam / defdam) * 100.0 >= defender.air_vs_air_percent:
        defdam *= 0.15
        attdam *= 0.10
    # attacker flees, same logic as above
    if (attdam >= 1.0) and (defdam / attdam) * 100.0 >= defender.air_vs_air_percent:
        defdam *= 0.50
        attdam *= 0.25
        attacker_flee = True
    if attdam == 0:
        attacker_flee = True

    # ========= Damage to attacking fleets =========#
    hptransport = attacking_fleet.transport * attstats["Transports"][1]
    hpcruiser = attacking_fleet.cruiser * attstats["Cruisers"][1]
    hpphantom = attacking_fleet.phantom * attstats["Phantoms"][1]
    hpbomber  = attacking_fleet.bomber * attstats["Bombers"][1]
    hpfighter = attacking_fleet.fighter * attstats["Fighters"][1]
    
    hpnecro = 0
    necro = Artefacts.objects.get(name="Scroll of the Necromancer")
    if necro.empire_holding == attacker.empire:
        hpnecro = necro.effect1 * 30
    
    hptotal = hptransport + hpcruiser + hpbomber + hpfighter + hpphantom + hpnecro

    damtransport = 0
    damcruiser = 0
    damphantom = 0
    damfighter = 0
    dambomber = 0
    damnecro = 0

    # percentage of damage that wil be received by the unit
    if hptotal:
        damtransport = hptransport / hptotal
        damcruiser = hpcruiser / hptotal
        damphantom = hpphantom / hptotal
        damfighter = hpfighter / hptotal
        dambomber = hpbomber / hptotal
    
    if hpnecro >=1:
        damnecro = hpnecro / hptotal

    # calc attacking/defending cruiser/fighter ratio,
    # transfer the damage from transports to other fleet depending on the ratios
    fb = 6 * defending_fleets["cruiser"] + defending_fleets["fighter"]
    fa = 0.0
    if fb >= 0.00001:
        fa = (6 * attacking_fleet.cruiser + attacking_fleet.fighter) / fb
    damtransport *= pow(2.50, -fa)

    fa = 0.0
    if defending_fleets["fighter"] > 0:
        fa = attacking_fleet.fighter / defending_fleets["fighter"]
    damcruiser *= pow(1.25, -fa)

    fb = defending_fleets["fighter"] + 3 * defending_fleets["cruiser"]
    fa = 0.0

    if fb >= 0.00001:
        fa = (attacking_fleet.fighter + 3 * attacking_fleet.cruiser) / fb
    dambomber *= pow(1.75, -fa)

    fb = damtransport + damcruiser + dambomber + damfighter + damphantom

    if fb >= 0.00001:
        fa = defdam / fb
        damtransport *= fa
        damcruiser *= fa
        dambomber *= fa
        damfighter *= fa
        damphantom *= fa
        damnecro *= fa

    if damtransport > hptransport:
        damcruiser += damtransport - hptransport
    if damcruiser > hpcruiser:
        dambomber += damcruiser - hpcruiser
    if dambomber > hpbomber:
        damfighter += dambomber - hpbomber
    if damfighter > hpfighter:
        damphantom += damfighter - hpfighter
    if damphantom > hpphantom:
        damcruiser += damphantom - hpphantom
    if damnecro > hpnecro:
        damphantom += damnecro - hpnecro
    
    neckilled = 0
    if necro.empire_holding == attacker.empire:
        neckilled = round(min(necro.effect1, damnecro * 100.0 / 30))
        necro.effect1 -= neckilled
        necro.save()
    
    attacker_losses = {"Bombers": round(min(attacking_fleet.bomber, dambomber / attstats["Bombers"][1])),
                       "Fighters": round(min(attacking_fleet.fighter, damfighter / attstats["Fighters"][1])),
                       "Transports": round(min(attacking_fleet.transport, damtransport / attstats["Transports"][1])),
                       "Cruisers": round(min(attacking_fleet.cruiser, damcruiser / attstats["Cruisers"][1])),
                       "Carriers": 0,
                       "Soldiers": 0, "Droids": 0, "Goliaths": 0,
                       "Phantoms": round(min(attacking_fleet.phantom, damphantom / attstats["Phantoms"][1])),
                       "Necromancers": neckilled}

    calc_lost_units_attacker(attacking_fleet, attacker_losses)
    attacking_fleet.save()

    # ========= Damage to defending fleets =========#
    hpcruiser = defending_fleets["cruiser"] * defstats["Cruisers"][1]
    hpphantom = defending_fleets["phantom"] * defstats["Phantoms"][1]
    hpfighter = defending_fleets["fighter"] * defstats["Fighters"][1]
    hpsats = attacked_planet.defense_sats * sats_defence

    hpnecro = 0
    if necro.empire_holding == defender.empire:
        hpnecro = necro.effect1 * 30 

    hptotal = hpcruiser + hpphantom + hpsats + hpfighter + hpnecro
    damcruiser = 0
    damphantom = 0
    damsats = 0
    damfighter = 0
    damnecro = 0

    if hptotal:
        damcruiser = hpcruiser / hptotal
        damphantom = hpphantom / hptotal
        damsats = hpsats / hptotal
        damfighter = hpfighter / hptotal
    
    if hpnecro >=1:
        damnecro = hpnecro / hptotal

    fa = 0.0
    if attacking_fleet.fighter > 0:
        fa = defending_fleets["fighter"] / attacking_fleet.fighter
    damcruiser *= pow(1.25, -fa)

    fb = damcruiser + damphantom + damsats + damnecro

    if fb >= 0.00001:
        fa = attdam / fb
        damcruiser *= fa
        damfighter *= fa
        damphantom *= fa
        damsats *= fa
        damnecro *= fa

    if damcruiser > hpcruiser:
        damfighter += damcruiser - hpcruiser
    if damfighter > hpfighter:
        damphantom += damfighter - hpfighter
    if damphantom > hpphantom:
        damsats += damphantom - hpphantom
    if damsats > hpsats:
        damcruiser += damsats - hpsats
    if damnecro > hpnecro:
        damphantom += damnnecro - hpnecro
    
    neckilled = 0
    if necro.empire_holding == defender.empire:
        neckilled = round(min(necro.effect1, damnecro * 100.0 / 30))
        necro.effect1 -= neckilled
        necro.save()
    
    defender_losses = {"Bombers": 0,
                       "Fighters": round(min(defending_fleets["fighter"], damfighter / 120)),
                       "Transports": 0,
                       "Cruisers": round(min(defending_fleets["cruiser"], damcruiser / defstats["Cruisers"][1])),
                       "Carriers": 0, "Soldiers": 0, "Droids": 0, "Goliaths": 0,
                       "Phantoms": round(min(defending_fleets["phantom"], damphantom / defstats["Phantoms"][1])),
                       "Defence Satellites": round(min(attacked_planet.defense_sats, damsats / sats_defence)),
                       "Necromancers": neckilled}

    attacked_planet.defense_sats -= defender_losses["Defence Satellites"]
    attacked_planet.save()

    defending_fleets["cruiser"] -= defender_losses["Cruisers"]
    defending_fleets["phantom"] -= defender_losses["Phantoms"]
    defending_fleets["fighter"] -= defender_losses["Fighters"]

    return attacker_flee, defender_flee, attacker_losses, defender_losses

####################
#      PHASE 3     #
####################
def phase3(attacking_fleet,
           defending_fleets,
           attstats, defstats,
           attfactor,
           deffactor,
           attacked_planet,
           attacker,
           defender,
           shields):
    attacker_flee = False
    defender_flee = False

    # ========= Calculate damage factors =========#
    attdam = attacking_fleet.bomber * attstats["Bombers"][2] + \
             attacking_fleet.phantom * attstats["Phantoms"][2] + \
             attacking_fleet.cruiser * attstats["Cruisers"][2]

    necro = Artefacts.objects.get(name="Scroll of the Necromancer")
    if necro.empire_holding == attacker.empire:
        attdam += necro.effect1 * 1

    defdam = defending_fleets["goliath"] * defstats["Goliaths"][0] + \
             defending_fleets["phantom"] * defstats["Phantoms"][2]
    virus = Artefacts.objects.get(name="t-Veronica")
    if virus.empire_holding == defender.empire:
        viruspop = attacked_planet.current_population * defstats["Goliaths"][0] / 100
        defdam += viruspop
        
    if necro.empire_holding == defender.empire:
        defdam += necro.effect1 * 1    
        
    if defdam > 0:
        if virus.empire_holding == defender.empire:
            defdam_goliath_fraction = ((defending_fleets["goliath"] * defstats["Goliaths"][0]) + viruspop) / defdam
        else: 
            defdam_goliath_fraction = defending_fleets["goliath"] * defstats["Goliaths"][0] / defdam

    else:
        defdam_goliath_fraction = 0

    attdam = attdam * attfactor * ((1.0 + 0.005 * attacker.research_percent_military) / \
                                   (1.0 + 0.005 * defender.research_percent_military))

    defdam = defdam * deffactor * ((1.0 + 0.005 * defender.research_percent_military) / \
                                   (1.0 + 0.005 * attacker.research_percent_military))


    if attdam >= 1.0:
        attdam -= attdam * (1.0 - pow(2.5, -(shields / attdam)))

    # ========= Determine if anyone will flee =========#
    # damage is too high defender flee
    if (defdam < 1.0) or (attdam / defdam) * 10.0 >= defender.ground_vs_air_percent:
        defender_flee = True
        return attacker_flee, defender_flee, {}, {}
    # defender flees, if settings are 100% this means attacker deals 10x more damage than defender
    if (attdam / defdam) * 100.0 >= defender.ground_vs_air_percent:
        defdam *= 0.15
        attdam *= 0.10
    # attacker flees, same logic as above
    if (attdam >= 1.0) and (defdam / attdam) * 100.0 >= defender.ground_vs_air_percent:
        defdam *= 0.30
        attdam *= 0.15
        attacker_flee = True
    if attdam == 0:
        attacker_flee = True


    # ========= Damage to attacking fleets =========#
    hptransport = attacking_fleet.transport * attstats["Transports"][3]
    hpcruiser = attacking_fleet.cruiser * attstats["Cruisers"][3]
    hpphantom = attacking_fleet.phantom * attstats["Phantoms"][3]
    hpbomber = attacking_fleet.bomber * attstats["Bombers"][3]
    
    hpnecro = 0
    necro = Artefacts.objects.get(name="Scroll of the Necromancer")
    if necro.empire_holding == attacker.empire:
        hpnecro = necro.effect1 * 30
    
    hptotal = hptransport + hpcruiser + hpbomber + hpphantom + hpnecro

    damtransport = 0
    damcruiser = 0
    damphantom = 0
    dambomber = 0
    damnecro = 0

    # percentage of damage that wil be received by the unit
    if hptotal:
        damtransport = hptransport / hptotal
        damcruiser = hpcruiser / hptotal
        damphantom = hpphantom / hptotal
        dambomber = hpbomber / hptotal
    
    if hpnecro >=1:
        damnecro = hpnecro / hptotal

    # calc attacking/defending goliath/bomber+cruiser ratio,
    # transfer the damage from transports to other fleet depending on the ratios
    if attacking_fleet.bomber > 0 or attacking_fleet.cruiser > 0:
        if virus.empire_holding == defender.empire:
            fa = (defending_fleets["goliath"] +( attacked_planet.current_population / 100))/ (attacking_fleet.bomber + attacking_fleet.cruiser)
        else:
            fa = defending_fleets["goliath"] / (attacking_fleet.bomber + attacking_fleet.cruiser)
    else:
        if virus.empire_holding == defender.empire:
            fa = defending_fleets["goliath"] +( attacked_planet.current_population / 100)
        else:
            fa = defending_fleets["goliath"]


    fb = damtransport + damcruiser + dambomber + damphantom + damnecro
    if fb >= 0.00001:
        fa = defdam / fb
        damtransport *= fa
        damcruiser *= fa
        dambomber *= fa
        damphantom *= fa
        damnecro *= fa

    if damtransport > hptransport:
        damcruiser += damtransport - hptransport
    if damcruiser > hpcruiser:
        dambomber += damcruiser - hpcruiser
    if dambomber > hpbomber:
        damphantom += dambomber - hpbomber
    if damphantom > hpphantom:
        damcruiser += damphantom - hpphantom
    if damnecro > hpnecro:
        damtransport += damnecro - hpnecro

    neckilled = 0
    if necro.empire_holding == attacker.empire:
        neckilled = round(min(necro.effect1, damnecro * 100.0 / 30))
        necro.effect1 -= neckilled
        necro.save()

    attacker_losses = {"Bombers": round(min(attacking_fleet.bomber, dambomber / attstats["Bombers"][3])),
                       "Fighters": 0,
                       "Transports": round(min(attacking_fleet.transport, damtransport / attstats["Transports"][3])),
                       "Cruisers": round(min(attacking_fleet.cruiser, damcruiser / attstats["Cruisers"][3])),
                       "Carriers": 0,
                       "Soldiers": 0, "Droids": 0, "Goliaths": 0,
                       "Phantoms": round(min(attacking_fleet.phantom, damphantom / attstats["Phantoms"][3])),
                       "Necromancers": neckilled}

    calc_lost_units_attacker(attacking_fleet, attacker_losses)
    attacking_fleet.save()

    # ========= Damage to defending fleets =========#
    hpgoliath  = defending_fleets["goliath"] * defstats["Goliaths"][1]
    hpphantom = defending_fleets["phantom"] * defstats["Phantoms"][3]
    
    virus = Artefacts.objects.get(name="t-Veronica")
    if virus.empire_holding == defender.empire:
        hppop = attacked_planet.current_population * defstats["Goliaths"][1] / 100
    else:
        hppop = 0
    
    hpnecro = 0
    if necro.empire_holding == defender.empire:
        hpnecro = necro.effect1 * 30 
    
    hptotal = hpcruiser + hpphantom + hppop + hpnecro

    damgoliath = 0
    damphantom = 0
    dampop = 0
    damnecro = 0

    if hptotal:
        damgoliath = hpgoliath / hptotal
        damphantom = hpphantom / hptotal
        dampop = hppop / hptotal
    
    if hpnecro >=1:
        damnecro = hpnecro / hptotal

    damgoliath *= attdam
    damphantom *= attdam
    dampop *= attdam
    damnecro *= attdam

    if damgoliath > hpgoliath:
        dampop += damgoliath - hpgoliath
    if damphantom > hpphantom:
        damgoliath += damphantom - hpphantom
    if dampop > hppop:    
        damphantom += dampop - hppop
    if damnecro > hpnecro:
        damphantom += damnnecro - hpnecro
    
    if virus.empire_holding == defender.empire:
        popkilled = round(min(attacked_planet.current_population, dampop * 100.0 / defstats["Goliaths"][3]))
    else:
        popkilled = 0
    
    necro = Artefacts.objects.get(name="Scroll of the Necromancer")
    neckilled = 0
    if necro.empire_holding == defender.empire:
        neckilled = round(min(necro.effect1, damnecro * 100.0 / 30))
        necro.effect1 -= neckilled
        necro.save()
        if popkilled >= 1:
            necro.effect1 += popkilled
            necro.save()
        
    defender_losses = {"Bombers": 0, "Fighters": 0,"Transports": 0,
                       "Cruisers": 0, "Carriers": 0, "Soldiers": 0, "Droids": 0,
                       "Goliaths": round(min(defending_fleets["goliath"], damgoliath / defstats["Goliaths"][1])),
                       "Phantoms": round(min(defending_fleets["phantom"], damphantom / defstats["Phantoms"][3])),
                       "Defence Satellites": 0, "Planet population": popkilled,
                       "Necromancers": neckilled}

    attacked_planet.defense_sats -= defender_losses["Defence Satellites"]
    attacked_planet.current_population -= popkilled
    attacked_planet.save()

    defending_fleets["goliath"] -= defender_losses["Goliaths"]
    defending_fleets["phantom"] -= defender_losses["Phantoms"]

    return attacker_flee, defender_flee, attacker_losses, defender_losses

####################
#      PHASE 4     #
####################
def phase4(attacking_fleet,
           defending_fleets,
           attstats, defstats,
           attfactor,
           deffactor,
           attacked_planet,
           attacker,
           defender,
           shields):
    attacker_flee = False
    defender_flee = False
    
    nrg = 0
    mins = 0
    crys = 0
    ectro = 0
    
    ironside = Artefacts.objects.get(name="Ironside Effect")
    if ironside.empire_holding == attacker.empire:
        nrg = round(defender.energy * 0.01)
        mins = round(defender.minerals * 0.005)
        crys = round(defender.crystals * 0.005)
        ectro = round(defender.ectrolium * 0.005)
    
    # ========= Calculate damage factors =========#
    attdam = attacking_fleet.soldier * attstats["Soldiers"][2] + \
             attacking_fleet.droid * attstats["Droids"][2] + \
             attacking_fleet.goliath * attstats["Goliaths"][2] + \
             attacking_fleet.phantom * attstats["Phantoms"][2]
    
    necro = Artefacts.objects.get(name="Scroll of the Necromancer")
    if necro.empire_holding == attacker.empire:
        attdam += necro.effect1 * 1
    
    defdam = defending_fleets["soldier"] * defstats["Soldiers"][2] + \
             defending_fleets["droid"] * defstats["Droids"][2] + \
             defending_fleets["goliath"] * defstats["Goliaths"][2] + \
             defending_fleets["phantom"] * defstats["Phantoms"][2]
    virus = Artefacts.objects.get(name="t-Veronica")
    if virus.empire_holding == defender.empire:
        viruspop = attacked_planet.current_population * defstats["Goliaths"][2] / 100
    else:
        viruspop = attacked_planet.current_population * defstats["Soldiers"][2] / 100
    
    defdam += viruspop

    if necro.empire_holding == defender.empire:
        defdam += necro.effect1 * 1

    bomber_modifier = attacking_fleet.bomber * defstats["Bombers"][2] + \
                      attacking_fleet.cruiser *  defstats["Cruisers"][2]

    if attdam > 0:
        fa = bomber_modifier / attdam
        if fa < 0.5:
            attdam += bomber_modifier
        else:
            attdam += 0.5 * attdam * pow(2.0 * fa, 0.35)

    attdam = attdam * attfactor * ((1.0 + 0.005 * attacker.research_percent_military) / \
                                   (1.0 + 0.005 * defender.research_percent_military))

    defdam = defdam * deffactor * ((1.0 + 0.005 * defender.research_percent_military) / \
                                   (1.0 + 0.005 * attacker.research_percent_military))

    if attdam >= 1.0:
        attdam -= attdam * (1.0 - pow(2.5, -(shields / attdam)))

    # ========= Determine if anyone will flee =========#
    # damage is too high defender flee
    if (defdam < 1.0) or (attdam / defdam) * 10.0 >= defender.ground_vs_ground_percent:
        defender_flee = True
        defender_losses = {"Energy": nrg,
                       "Mineral": mins,
                       "Crystal": crys,
                       "Ectrolium": ectro}
        attacker.energy += nrg
        attacker.minerals += mins
        attacker.crystals += crys
        attacker.ectrolium += ectro
        attacker.save()
        
        defender.energy -= nrg
        defender.minerals -= mins
        defender.crystals -= crys
        defender.ectrolium -= ectro
        defender.save() 
        return attacker_flee, defender_flee, {}, defender_losses
    # defender flees, if settings are 100% this means attacker deals 10x more damage than defender
    if (attdam / defdam) * 100.0 >= defender.ground_vs_ground_percent:
        defdam *= 0.15
        attdam *= 0.10
    # attacker flees, same logic as above
    if (attdam >= 1.0) and (defdam / attdam) * 100.0 >= defender.ground_vs_ground_percent:
        defdam *= 0.10
        attdam *= 0.20
        attacker_flee = True


    # ========= Damage to attacking fleets =========#
    hpsoldier  = attacking_fleet.soldier * attstats["Soldiers"][3]
    hpdroid  = attacking_fleet.droid * attstats["Droids"][3]
    hpphantom = attacking_fleet.phantom * attstats["Phantoms"][3]
    hpgoliath  = attacking_fleet.goliath * attstats["Goliaths"][3]
    hpnecro = 0
    
    if necro.empire_holding == attacker.empire:
        hpnecro = necro.effect1 * 30
    
    hptotal = hpsoldier + hpdroid + hpgoliath + hpphantom
    
    damsoldier = 0
    damdroid = 0
    damgoliath = 0
    damphantom = 0
    damnecro = 0

    # percentage of damage that wil be received by the unit
    if hptotal:
        damsoldier = hpsoldier / hptotal
        damdroid = hpdroid / hptotal
        damgoliath = hpgoliath / hptotal
        damphantom = hpphantom / hptotal
    
    if hpnecro >=1:
        damnecro = hpnecro / hptotal

    # transfer the damage from goliahs to droids and soldiers
    fb = defending_fleets["soldier"] + defending_fleets["goliath"]
    fa = 0.0
    if fb >= 0.00001:
        fa = (attacking_fleet.soldier + attacking_fleet.droid) / fb
    damgoliath *= pow(1.50, -fa)

    fb = damsoldier + damdroid + damgoliath + damphantom + damnecro

    if fb >= 0.00001:
        fa = defdam / fb
        damsoldier *= fa
        damdroid *= fa
        damgoliath *= fa
        damphantom *= fa
        damnecro *= fa

    if damsoldier > hpsoldier:
        damdroid += damsoldier - hpsoldier
    if damdroid > hpdroid:
        damgoliath += damdroid - hpdroid
    if damgoliath > hpgoliath:
        damsoldier += damgoliath - hpgoliath
    if damsoldier > hpsoldier:
        damphantom += damsoldier - hpsoldier
    if damphantom > hpphantom:
        damdroid += damphantom - hpphantom
    if damnecro > hpnecro:
        damphantom += damnecro - hpnecro
    
    neckilled = 0
    if necro.empire_holding == attacker.empire:
        neckilled = round(min(necro.effect1, damnecro * 100.0 / 30))
        necro.effect1 -= neckilled
        necro.save()
    
    attacker_losses = {"Bombers": 0, "Fighters": 0, "Transports": 0, "Cruisers": 0, "Carriers": 0,
                       "Soldiers": round(min(attacking_fleet.soldier, damsoldier / attstats["Soldiers"][3])),
                       "Droids": round(min(attacking_fleet.droid, damdroid / attstats["Droids"][3])),
                       "Goliaths": round(min(attacking_fleet.goliath, damgoliath / attstats["Goliaths"][3])),
                       "Phantoms": round(min(attacking_fleet.phantom, damphantom / attstats["Phantoms"][3])),
                       "Necromancers": neckilled}
    
    calc_lost_units_attacker(attacking_fleet, attacker_losses)
    attacking_fleet.save()

    # ========= Damage to defending fleets =========#
    hpgoliath  = defending_fleets["goliath"] * defstats["Goliaths"][3]
    hpphantom = defending_fleets["phantom"] * defstats["Phantoms"][3]
    hpsoldier = defending_fleets["soldier"] * defstats["Soldiers"][3]
    hpdroid = defending_fleets["droid"] * defstats["Droids"][3]
    virus = Artefacts.objects.get(name="t-Veronica")
    if virus.empire_holding == defender.empire:
        hppop = attacked_planet.current_population * defstats["Goliaths"][3] / 100
    else:
        hppop = attacked_planet.current_population * defstats["Soldiers"][3] / 100
    
    hpnecro = 0
    necro = Artefacts.objects.get(name="Scroll of the Necromancer")
    if necro.empire_holding == defender.empire:
        hpnecro = necro.effect1 * 30  
    
    hptotal = hpsoldier + hpdroid + hpgoliath + hpphantom + hppop + hpnecro

    damsoldier = 0
    damdroid = 0
    damgoliath = 0
    damphantom = 0
    dampop =  0
    damnecro = 0

    if hptotal:
        damsoldier = hpsoldier / hptotal
        damdroid = hpdroid / hptotal
        damgoliath = hpgoliath / hptotal
        damphantom = hpphantom / hptotal
        dampop = hppop / hptotal
    
    if hpnecro >=1:
        damnecro = hpnecro / hptotal

    # transfer the damage from goliahs to droids and soldiers
    fb = (attacking_fleet.soldier + attacking_fleet.droid)
    fa = 0.0
    if fb >= 0.00001:
        fa = (defending_fleets["soldier"] + defending_fleets["goliath"]) / fb
    damgoliath *= pow(1.50, -fa)

    fb = damsoldier + damdroid + damgoliath + damphantom + dampop + damnecro

    if fb >= 0.00001:
        fa = attdam / fb
        damsoldier *= fa
        damdroid *= fa
        damgoliath *= fa
        damphantom *= fa
        dampop *= fa
        damnecro *= fa

    if damsoldier > hpsoldier:
        damdroid += damsoldier - hpsoldier
    if damdroid > hpdroid:
        damgoliath += damdroid - hpdroid
    if damgoliath > hpgoliath:
        dampop += damgoliath - hpgoliath
    if dampop > hppop:
        damsoldier += dampop - hppop
    if damsoldier > hpsoldier:
        damphantom += damsoldier - hpsoldier
    if damphantom > hpphantom:
        damdroid += damphantom - hpphantom
    if damnecro > hpnecro:
        damphantom += damnnecro - hpnecro
        
    virus = Artefacts.objects.get(name="t-Veronica")
    if virus.empire_holding == defender.empire:
        popkilled = round(min(attacked_planet.current_population, dampop * 100.0 / defstats["Goliaths"][3]))
    else:
        popkilled = round(min(attacked_planet.current_population, dampop * 100.0 / defstats["Soldiers"][3]))
    
    neckilled = 0
    if necro.empire_holding == defender.empire:
        neckilled = round(min(necro.effect1, damnecro * 100.0 / 30))
        necro.effect1 -= neckilled
        necro.save()
        if popkilled >= 1:
            necro.effect1 += popkilled
            necro.save()        
    
    defender_losses = {"Bombers": 0, "Fighters": 0,"Transports": 0,
                       "Cruisers": 0, "Carriers": 0,
                       "Soldiers": round(min(defending_fleets["soldier"], damsoldier / defstats["Soldiers"][3])),
                       "Droids": round(min(defending_fleets["droid"], damdroid / defstats["Droids"][3])),
                       "Goliaths": round(min(defending_fleets["goliath"], damgoliath / defstats["Goliaths"][3])),
                       "Phantoms": round(min(defending_fleets["phantom"], damphantom / defstats["Phantoms"][3])),
                       "Defence Satellites": 0,
                       "Planet population": popkilled,
                       "Necromancers": neckilled,
                       "Energy": nrg,
                       "Mineral": mins,
                       "Crystal": crys,
                       "Ectrolium": ectro}

    attacked_planet.current_population -= popkilled
    attacked_planet.save()

    defending_fleets["goliath"] -= defender_losses["Goliaths"]
    defending_fleets["phantom"] -= defender_losses["Phantoms"]
    defending_fleets["droid"] -= defender_losses["Droids"]
    defending_fleets["soldier"] -= defender_losses["Soldiers"]

    # calculate the ground attack /defence after the battle to see if the planet is taken
    attdam = attacking_fleet.soldier * attstats["Soldiers"][2] + \
             attacking_fleet.droid * attstats["Droids"][2] + \
             attacking_fleet.goliath * attstats["Goliaths"][2] + \
             attacking_fleet.phantom * attstats["Phantoms"][2]

    defdam = defending_fleets["soldier"] * defstats["Soldiers"][2] + \
             defending_fleets["droid"] * defstats["Droids"][2] + \
             defending_fleets["goliath"] * defstats["Goliaths"][2] + \
             defending_fleets["phantom"] * defstats["Phantoms"][2] + \
             necro.effect1 * 30
    virus = Artefacts.objects.get(name="t-Veronica")
    if virus.empire_holding == defender.empire:
        viruspop = attacked_planet.current_population * defstats["Goliaths"][2] / 100
    else:
        viruspop = attacked_planet.current_population * defstats["Soldiers"][2] / 100
    
    defdam += viruspop
    
    attacker.energy += nrg
    attacker.minerals += mins
    attacker.crystals += crys
    attacker.ectrolium += ectro
    attacker.save()
    
    defender.energy -= nrg
    defender.minerals -= mins
    defender.crystals -= crys
    defender.ectrolium -= ectro
    defender.save() 
    
    if attacker_flee or attdam <= defdam:
        attacker_flee = True
    else:
        defender_flee = True

    return attacker_flee, defender_flee, attacker_losses, defender_losses
    msg += str(attacking_fleet.owner)