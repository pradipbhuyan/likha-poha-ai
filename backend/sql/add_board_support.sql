alter table public.profiles
add column if not exists board text not null default 'CBSE';

update public.profiles
set board = 'CBSE'
where board is null
   or trim(board) = '';

alter table public.rag_documents
add column if not exists board text not null default 'CBSE';

update public.rag_documents
set board = 'CBSE'
where board is null
   or trim(board) = '';

alter table public.syllabus_chapter_overrides
add column if not exists board text not null default 'CBSE';

update public.syllabus_chapter_overrides
set board = 'CBSE'
where board is null
   or trim(board) = '';

create unique index if not exists syllabus_chapter_overrides_grade_mode_subject_key
on public.syllabus_chapter_overrides (grade, mode, subject);

alter table public.syllabus_subject_overrides
add column if not exists board text not null default 'CBSE';

update public.syllabus_subject_overrides
set board = 'CBSE'
where board is null
   or trim(board) = '';

create unique index if not exists syllabus_subject_overrides_grade_mode_key
on public.syllabus_subject_overrides (grade, mode);

alter table public.doubt_history
add column if not exists board text not null default 'CBSE';

update public.doubt_history
set board = 'CBSE'
where board is null
   or trim(board) = '';
