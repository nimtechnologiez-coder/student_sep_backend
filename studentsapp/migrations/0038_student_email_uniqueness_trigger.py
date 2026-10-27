from django.db import migrations

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION enforce_student_email_unique()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.email IS NOT NULL AND TRIM(NEW.email) <> '' THEN
        IF TG_OP = 'INSERT' THEN
            IF EXISTS (
                SELECT 1 FROM studentsapp_student
                WHERE LOWER(TRIM(email)) = LOWER(TRIM(NEW.email))
            ) THEN
                RAISE EXCEPTION 'This email address is already registered.' USING ERRCODE = 'unique_violation';
            END IF;
        ELSIF TG_OP = 'UPDATE' THEN
            IF LOWER(TRIM(COALESCE(NEW.email, ''))) <> LOWER(TRIM(COALESCE(OLD.email, ''))) THEN
                IF EXISTS (
                    SELECT 1 FROM studentsapp_student
                    WHERE LOWER(TRIM(email)) = LOWER(TRIM(NEW.email))
                      AND id <> OLD.id
                ) THEN
                    RAISE EXCEPTION 'This email address is already registered.' USING ERRCODE = 'unique_violation';
                END IF;
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_enforce_student_email_unique ON studentsapp_student;
CREATE TRIGGER trg_enforce_student_email_unique
BEFORE INSERT OR UPDATE OF email ON studentsapp_student
FOR EACH ROW
EXECUTE FUNCTION enforce_student_email_unique();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS trg_enforce_student_email_unique ON studentsapp_student;
DROP FUNCTION IF EXISTS enforce_student_email_unique();
"""

class Migration(migrations.Migration):

    dependencies = [
        ('studentsapp', '0037_feepayment_order_id_feepayment_payment_status'),
    ]

    operations = [
        migrations.RunSQL(TRIGGER_SQL, reverse_sql=REVERSE_SQL),
    ]
