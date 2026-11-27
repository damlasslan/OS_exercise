do $test$
declare u uuid:=gen_random_uuid(); other_user uuid:=gen_random_uuid(); assignment uuid; attempt uuid; mail text:=u::text||'@example.invalid';
begin
 begin
 insert into neon_auth."user"(id,name,email,"emailVerified","createdAt","updatedAt") values(u,'Synthetic test',mail,false,now(),now());
 insert into lab.roster(student_id,email,section,auth_id) values(u::text,mail,'TEST',u::text);
 if lab.verified_student(u) is not null then raise exception 'unverified accepted'; end if;
 update neon_auth."user" set "emailVerified"=true where id=u;
 insert into lab.assignments(title,opens_at,closes_at) values('Synthetic test',now()-interval '1 hour',now()+interval '1 hour') returning id into assignment;
 insert into lab.attempts(assignment_id,student_id,attempt_no,case_no,workload) values(assignment,u::text,1,1,'{}') returning id into attempt;
 if lab.save_draft(u,attempt,0,'{"architecture":"test"}') is distinct from 1 then raise exception 'write failed'; end if;
 if lab.save_draft(u,attempt,0,'{}') is not null then raise exception 'stale write accepted'; end if;
 if lab.save_draft(other_user,attempt,1,'{}') is not null or exists(select from lab.load_draft(other_user,attempt)) then raise exception 'foreign access'; end if;
 if (select draft from lab.load_draft(u,attempt)) is distinct from '{"architecture":"test"}'::jsonb then raise exception 'resume failed'; end if;
 update neon_auth."user" set banned=true where id=u;
 if lab.verified_student(u) is not null then raise exception 'banned accepted'; end if;
 raise exception using errcode='ZX001',message='roll back successful fixtures';
 exception when sqlstate 'ZX001' then null;
 end;
end $test$;
