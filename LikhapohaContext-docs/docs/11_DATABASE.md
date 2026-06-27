# Database Standards

## Migration Rules

- Migrations must be idempotent where possible.
- Prefer additive migrations.
- Avoid destructive changes without explicit approval and rollback plan.
- Handle existing duplicate data before adding unique constraints.
- Document required manual Supabase migrations.

## Important Tables/Concepts

- profiles
- subscription_payments
- offer_redemptions
- platform_audit_logs
- subscription_timeline
- teacher_student_assignments
- teacher_invitations
- teacher_classrooms
- teacher_classroom_students
- teacher_tasks
- teacher_student_notes
- teacher_parent_messages

## Indexing

Add indexes for high-use fields such as:

- user_id
- teacher_id
- student_id
- parent_id
- classroom_id
- status
- created_at
- razorpay_payment_id
- razorpay_order_id
- idempotency_key

## RLS

Use RLS carefully. Do not create permissive `USING (true)` policies for sensitive audit/timeline tables. Backend service role can bypass RLS; normal users should not read admin/audit data.
