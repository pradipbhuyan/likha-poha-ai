-- Mobile OTA (over-the-air) bundle releases — self-hosted @capgo/capacitor-updater
-- backend. Tracks each published web-bundle release the Android app can fetch
-- and apply without going through a Play Store review cycle.
--
-- Purely additive — a new table, no existing schema touched.

create table if not exists public.mobile_ota_releases (
  id                uuid          primary key default gen_random_uuid(),
  platform          text          not null default 'android'
                    check (platform in ('android', 'ios')),
  channel           text          not null default 'production',
  version           text          not null,
  bundle_url        text          not null,
  checksum          text          not null default '',
  -- Floor on the native shell's Android versionCode required to accept this
  -- bundle. Guards against an OTA bundle that assumes a native plugin/API
  -- only present in a newer native build being served to an older install
  -- that doesn't have it — see mobile_ota_service.py.
  min_version_code  integer       not null default 1,
  is_active         boolean       not null default true,
  notes             text          not null default '',
  created_at        timestamptz   not null default now()
);

create index if not exists idx_mobile_ota_releases_lookup
  on public.mobile_ota_releases (platform, channel, is_active, created_at desc);

alter table public.mobile_ota_releases enable row level security;

create policy "service_role_all_mobile_ota_releases"
  on public.mobile_ota_releases for all
  to service_role using (true) with check (true);
