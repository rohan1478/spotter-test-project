from django.core.management.base import BaseCommand
from django.conf import settings
from stations.tasks import ingest_fuel_prices_csv


class Command(BaseCommand):
    help = "Ingest fuel prices from CSV (runs synchronously, or dispatches to Celery with --async)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-path",
            default=settings.FUEL_PRICES_CSV_PATH,
            help="Path to the fuel prices CSV file",
        )
        parser.add_argument(
            "--async",
            action="store_true",
            dest="run_async",
            help="Dispatch to Celery instead of running synchronously",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        if options["run_async"]:
            ingest_fuel_prices_csv.delay(csv_path)
            self.stdout.write(self.style.SUCCESS(f"Task dispatched for: {csv_path}"))
        else:
            result = ingest_fuel_prices_csv(csv_path)
            self.stdout.write(self.style.SUCCESS(f"Done: {result}"))
