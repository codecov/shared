def run_sql(schema_editor):
    schema_editor.execute(
        """
        create or replace function owners_before_insert_or_update() returns trigger as $$
        begin
            -- user has changed name or deleted and invalidate sessions
            with _owners as (update owners
                            set username = null
                            where service = new.service
                            and username = new.username::citext
                            returning ownerid)
            delete from sessions where ownerid in (select ownerid from _owners);
            return new;
        end;
        $$ language plpgsql;

        create trigger owners_before_insert before insert on owners
        for each row
        execute procedure owners_before_insert_or_update();

        create trigger owners_before_update before update on owners
        for each row
        when (new.username is not null and new.username is distinct from old.username)
        execute procedure owners_before_insert_or_update();
    """
    )
