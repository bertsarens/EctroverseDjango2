from django.core.management.base import BaseCommand, CommandError
from app.models import *
import time
import random
from django.db import transaction



class Command(BaseCommand): # must be called command, use file name to name the functionality
    @transaction.atomic
    def handle(self, *args, **options):
        start_t = time.time()
        arte = Artefacts.objects.get(name="The Recycler")
        if arte.empire_holding != None:
            for player in UserStatus.objects.filter(empire=arte.empire_holding):
                fund = player.energy_decay * (0.01 + (player.research_percent_tech/200))
                player.current_research_funding += fund
                player.save()
        print("Generating recycler took " + str(time.time() - start_t) + "seconds")
