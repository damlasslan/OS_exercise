-- Students may open any of the five cases and continue each one where they left off.
-- One attempt per case per student and assignment; attempt_no only numbers them in the order they were opened.
-- Run once on the development database after release.sql. The transaction rolls back if a student
-- already has two attempts for the same case, so nothing is changed in that situation.
begin;
alter table lab.attempts drop constraint if exists attempts_attempt_no_check;
alter table lab.attempts add constraint attempts_attempt_no_check check (attempt_no between 1 and 5);
create unique index if not exists attempts_one_per_case on lab.attempts(assignment_id, student_id, case_no);

create or replace function lab.guard_attempt() returns trigger language plpgsql set search_path=pg_catalog,lab as $$
declare deadline timestamptz; opening timestamptz;
begin
 select opens_at,closes_at into opening,deadline from lab.assignments where id=new.assignment_id;
 if opening is null or deadline is null or now()<opening or now()>deadline then raise exception 'Assignment is not open'; end if;
 if tg_op='INSERT' then
 if not exists(select from lab.roster where student_id=new.student_id) then raise exception 'Attempt not authorized'; end if;
 if new.version<>0 or new.submitted_at is not null then raise exception 'Invalid initial state'; end if;
 else
 if old.submitted_at is not null then
   if new.submitted_at is not null or new.draft is distinct from old.draft
     or not exists (select from lab.instructors where auth_id=current_setting('oslab.reopening_instructor',true))
   then raise exception 'Submission is locked'; end if;
 end if;
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

comment on column lab.roster.allowed_attempts is 'Unused since multi-case.sql: students may open one attempt for each of the five cases.';
commit;
