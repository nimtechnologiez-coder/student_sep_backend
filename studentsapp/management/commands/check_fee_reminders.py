from django.core.management.base import BaseCommand
from studentsapp.fee_reminders import check_and_create_fee_reminders


class Command(BaseCommand):
    help = 'Checks pending fee payments and generates 7-day upcoming and overdue reminders.'

    def handle(self, *args, **options):
        self.stdout.write("Checking fee payment due dates...")
        created = check_and_create_fee_reminders()
        self.stdout.write(self.style.SUCCESS(f"Fee reminder check complete. Created {created} new reminder(s)."))
