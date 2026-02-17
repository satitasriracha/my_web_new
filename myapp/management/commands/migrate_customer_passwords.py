from django.core.management.base import BaseCommand
from myapp.models import Customer

class Command(BaseCommand):
    help = "Migrate all plain text Customer passwords to hashed format"

    def handle(self, *args, **options):
        updated = 0
        skipped = 0

        for customer in Customer.objects.all():
            pw = customer.password

            # ถ้า password ว่าง → ข้าม
            if not pw:
                skipped += 1
                continue

            # ถ้า password ยังไม่ใช่ hash (ยังไม่ขึ้นต้นด้วย pbkdf2_)
            if not pw.startswith("pbkdf2_"):
                raw_pw = pw
                customer.set_password(raw_pw)
                customer.save(update_fields=["password"])
                updated += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Updated: {customer.customer_id} - {customer.name}"
                ))
            else:
                skipped += 1

        self.stdout.write(self.style.NOTICE(
            f"✅ Migration finished. Updated: {updated}, Skipped: {skipped}"
        ))
