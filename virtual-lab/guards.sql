create or replace function lab.guard_attempt() returns trigger language plpgsql set search_path=pg_catalog,lab as $$
declare deadline timestamptz; opening timestamptz; permitted int;
begin
 select opens_at,closes_at into opening,deadline from lab.assignments where id=new.assignment_id;
 if opening is null or deadline is null or now()<opening or now()>deadline then raise exception 'Assignment is not open'; end if;
 if tg_op='INSERT' then
 select allowed_attempts into permitted from lab.roster where student_id=new.student_id;
 if permitted is null or new.attempt_no>permitted then raise exception 'Attempt not authorized'; end if;
 if new.version<>0 or new.submitted_at is not null then raise exception 'Invalid initial state'; end if;
 else
 if old.submitted_at is not null then raise exception 'Submission is locked'; end if;
 if (new.id,new.assignment_id,new.student_id,new.attempt_no,new.case_no,new.workload) is distinct from (old.id,old.assignment_id,old.student_id,old.attempt_no,old.case_no,old.workload) then raise exception 'Attempt identity and workload are immutable'; end if;
 if new.version<>old.version+1 then raise exception 'Version conflict'; end if;
 new.updated_at=now();
 if new.submitted_at is not null then
 if (select count(*) from lab.predictions where attempt_id=old.id and experiment in ('cpu','sync','vm','fs'))<>4 then raise exception 'Missing locked predictions'; end if;
 if not (new.draft ?& array['architecture','evaluation']) then raise exception 'Missing written sections'; end if;
 new.submitted_at=now();
 end if;
 end if;
 return new;
end $$;

create trigger lab_attempt_guard before insert or update on lab.attempts for each row execute function lab.guard_attempt();

create or replace function lab.guard_prediction() returns trigger language plpgsql set search_path=pg_catalog,lab as $$
declare a lab.attempts%rowtype; opening timestamptz; deadline timestamptz;
begin
 if tg_op<>'INSERT' then raise exception 'Original predictions are immutable'; end if;
 if new.experiment not in ('cpu','sync','vm','fs') then raise exception 'Unknown experiment'; end if;
 if jsonb_typeof(new.answers)<>'object' or new.answers='{}'::jsonb then raise exception 'Missing prediction'; end if;
 select * into a from lab.attempts where id=new.attempt_id for update;
 select opens_at,closes_at into opening,deadline from lab.assignments where id=a.assignment_id;
 if a.id is null or a.submitted_at is not null or opening is null or deadline is null or now()<opening or now()>deadline then raise exception 'Attempt closed'; end if;
 new.locked_at=now(); return new;
end $$;

create trigger lab_prediction_guard before insert or update or delete on lab.predictions for each row execute function lab.guard_prediction();

create or replace function lab.guard_run() returns trigger language plpgsql set search_path=pg_catalog,lab as $$
begin
 if tg_op<>'INSERT' then raise exception 'Experiment history is append-only'; end if;
 if not exists(select 1 from lab.predictions where attempt_id=new.attempt_id and experiment=new.experiment) then raise exception 'Lock a prediction first'; end if;
 new.created_at=now(); return new;
end $$;

create trigger lab_run_guard before insert or update or delete on lab.experiment_runs for each row execute function lab.guard_run();
