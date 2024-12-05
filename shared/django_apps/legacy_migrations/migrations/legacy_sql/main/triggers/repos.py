def run_sql(schema_editor):
    schema_editor.execute(
        """
        create or replace function repos_before_insert_or_update() returns trigger as $$
        begin
            -- repo name changed or deleted
            update repos
            set name = null,
                deleted = true,
                active = false,
                activated = false
            where ownerid = new.ownerid
            and name = new.name;
            return new;
        end;
        $$ language plpgsql;

        create trigger repos_before_insert before insert on repos
        for each row
        execute procedure repos_before_insert_or_update();

        create trigger repos_before_update before update on repos
        for each row
        when (new.name is not null and new.name is distinct from old.name)
        execute procedure repos_before_insert_or_update();
    """
    )
