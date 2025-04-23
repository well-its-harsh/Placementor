from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Remove duplicate users with the same email, keeping only the first. Optionally reset password.'

    def handle(self, *args, **options):
        seen_emails = set()
        duplicates = []
        for user in User.objects.all().order_by('date_joined'):
            if user.email in seen_emails:
                duplicates.append(user)
            else:
                seen_emails.add(user.email)
        for user in duplicates:
            self.stdout.write(f'Deleting duplicate user: {user.email} (id={user.id})')
            user.delete()
        self.stdout.write(self.style.SUCCESS(f'Removed {len(duplicates)} duplicate users.'))

        # Optional: Reset password for all users to a default value (for demo/testing)
        # for user in User.objects.all():
        #     user.set_password('changeme123')
        #     user.save()
        # self.stdout.write(self.style.SUCCESS('Reset password for all users to "changeme123".'))
