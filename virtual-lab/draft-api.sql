begin;
-- Called only by a trusted backend after validation of the Neon Auth session.
-- Exact roster email and preassigned auth_id must both match.
create or replace function lab.verified_student(p_subject uuid)
returns text language sql stable security invoker set search_path=pg_catalog as $$
  select r.student_id from lab.roster r join neon_auth."user" u
    on r.auth_id=u.id::text and r.email=u.email
  where u.id=p_subject and u."emailVerified" and not coalesce(u.banned,false)
$$;

create or replace function lab.load_draft(p_subject uuid,p_attempt uuid)
returns table(draft jsonb,version integer,submitted_at timestamptz)
language sql stable security invoker set search_path=pg_catalog as $$
  select a.draft,a.version,a.submitted_at from lab.attempts a
  where a.id=p_attempt and a.student_id=lab.verified_student(p_subject)
$$;

create or replace function lab.save_draft(p_subject uuid,p_attempt uuid,p_version integer,p_draft jsonb)
returns integer language plpgsql security invoker set search_path=pg_catalog as $$
declare saved_version integer;
begin
  if jsonb_typeof(p_draft) is distinct from 'object' or octet_length(p_draft::text)>131072 then
    raise exception 'Invalid draft' using errcode='22023';
  end if;
  update lab.attempts a set draft=p_draft, version=a.version+1
    where a.id=p_attempt and a.student_id=lab.verified_student(p_subject)
      and a.version=p_version and a.submitted_at is null
    returning a.version into saved_version;
  return saved_version;
end $$;

revoke all on function lab.verified_student(uuid), lab.load_draft(uuid,uuid), lab.save_draft(uuid,uuid,integer,jsonb) from public;
commit;
