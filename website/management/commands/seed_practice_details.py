from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Add original practice details without replacing customized text or existing sections.'

    def handle(self, *args, **options):
        migration = import_module('website.migrations.0016_seed_practice_details')
        migration.seed_details(apps, SimpleNamespace(connection=connection))
        self.stdout.write('Practice detail sections initialized; existing edits preserved.')
