# v4.6.1
def run_sql(schema_editor):
    schema_editor.execute(
        """
        ALTER TABLE reports_uploadleveltotals ALTER COLUMN coverage DROP NOT NULL;
        ALTER TABLE reports_reportleveltotals ALTER COLUMN coverage DROP NOT NULL;

        ALTER TABLE owners ALTER COLUMN student SET DEFAULT FALSE;

        UPDATE owners SET student=false WHERE student is NULL;
    """
    )
