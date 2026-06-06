-- Audit RAG document metadata used by syllabus dropdowns.
--
-- Run this first. It DOES NOT update anything. It shows rows where the stored
-- title/chapter metadata is likely too weak for safe dropdown generation, and
-- provides a suggested UPDATE statement for each row.
--
-- After reviewing the output, copy only the suggested_update_sql lines you trust
-- into a new SQL editor tab and run them.

with normalized_documents as (
  select
    id,
    coalesce(nullif(trim(board), ''), 'CBSE') as board,
    nullif(trim(grade), '') as grade,
    nullif(trim(subject), '') as subject,
    nullif(trim(chapter), '') as chapter,
    nullif(trim(title), '') as title,
    created_at,
    concat_ws(
      ' - ',
      concat_ws(
        ' ',
        coalesce(nullif(trim(board), ''), 'CBSE'),
        nullif(trim(grade), ''),
        nullif(trim(subject), ''),
        'Text Book'
      ),
      nullif(trim(chapter), '')
    ) as suggested_title
  from public.rag_documents
),
suspect_documents as (
  select
    *,
    array_remove(array[
      case when grade is null then 'missing grade' end,
      case when subject is null then 'missing subject' end,
      case when chapter is null then 'missing chapter' end,
      case when title is null then 'missing title' end,
      case when title ilike '%uploaded book content%' then 'generic title' end,
      case when grade is not null and title is not null and title not ilike '%' || grade || '%' then 'title missing grade' end,
      case when subject is not null and title is not null and title not ilike '%' || subject || '%' then 'title missing subject' end,
      case when chapter is not null and title is not null and title not ilike '%' || chapter || '%' then 'title missing chapter' end
    ], null) as issues
  from normalized_documents
)
select
  id,
  board,
  grade,
  subject,
  chapter,
  title as current_title,
  suggested_title,
  issues,
  format(
    'update public.rag_documents set title = %L where id = %L;',
    suggested_title,
    id
  ) as suggested_update_sql
from suspect_documents
where array_length(issues, 1) > 0
order by grade, board, subject, chapter, created_at;

-- Optional duplicate check. Same grade + board + subject + chapter should be
-- intentional, otherwise dropdown counts can look confusing.
select
  coalesce(nullif(trim(board), ''), 'CBSE') as board,
  grade,
  subject,
  chapter,
  count(*) as document_count,
  array_agg(id order by created_at) as document_ids,
  array_agg(title order by created_at) as titles
from public.rag_documents
group by coalesce(nullif(trim(board), ''), 'CBSE'), grade, subject, chapter
having count(*) > 1
order by grade, board, subject, chapter;
