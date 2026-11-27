begin;
create table if not exists lab.evidence(attempt_id uuid not null references lab.attempts, kind text not null check(kind in ('diagram','baseline','load')), png bytea not null check(octet_length(png) between 24 and 1200000), primary key(attempt_id,kind)); alter table lab.evidence enable row level security; revoke all on lab.evidence from public;
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


create or replace function lab.reopen_synthetic(p_instructor uuid,p_attempt uuid) returns boolean
language plpgsql security invoker set search_path=pg_catalog as $$
begin
 if not exists(select from lab.instructors i join neon_auth."user" u on u.id::text=i.auth_id where u.id=p_instructor and u."emailVerified" and not coalesce(u.banned,false) and right(lower(u.email),16)='@example.invalid') then return false; end if;
 perform set_config('oslab.reopening_instructor',p_instructor::text,true);
 update lab.attempts a set submitted_at=null,version=version+1 from lab.roster r where r.student_id=a.student_id and right(lower(r.email),16)='@example.invalid' and a.id=p_attempt and a.submitted_at is not null;
 return found;
end $$;
revoke all on function lab.reopen_synthetic(uuid,uuid) from public;
commit;
