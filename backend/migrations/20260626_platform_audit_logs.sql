-- Migration: platform_audit_logs table
-- Append-only audit trail for critical business events.
-- Never stores plaintext passwords or API secrets.

CREATE TABLE IF NOT EXISTS public.platform_audit_logs (
  id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id  uuid,                          -- who triggered the event (null = system)
  target_user_id uuid,                          -- user affected (null = not applicable)
  event_type     text        NOT NULL,           -- e.g. payment.verified, student.created
  entity_type    text,                           -- e.g. payment, student, parent_child_link
  entity_id      text,                           -- primary key of the entity (order_id, user_id…)
  metadata       jsonb       NOT NULL DEFAULT '{}'::jsonb,
  ip_address     text,
  user_agent     text,
  created_at     timestamptz NOT NULL DEFAULT now()
);

-- Audit logs are append-only — no UPDATE or DELETE allowed via normal roles.
ALTER TABLE public.platform_audit_logs ENABLE ROW LEVEL SECURITY;

-- Read-only for service_role (backend)
CREATE POLICY "audit_logs_service_read" ON public.platform_audit_logs
  FOR SELECT USING (true);

-- Efficient queries by actor, target, event type, and time
CREATE INDEX IF NOT EXISTS audit_logs_actor_idx    ON public.platform_audit_logs (actor_user_id);
CREATE INDEX IF NOT EXISTS audit_logs_target_idx   ON public.platform_audit_logs (target_user_id);
CREATE INDEX IF NOT EXISTS audit_logs_event_idx    ON public.platform_audit_logs (event_type);
CREATE INDEX IF NOT EXISTS audit_logs_created_idx  ON public.platform_audit_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS audit_logs_entity_idx   ON public.platform_audit_logs (entity_type, entity_id);

COMMENT ON TABLE public.platform_audit_logs IS
  'Immutable audit trail for payments, subscriptions, admin actions, and teacher/parent events.';
