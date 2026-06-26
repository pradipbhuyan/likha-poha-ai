-- Migration: rename subscription plans to new branding
-- Run in Supabase SQL editor (or already applied via Python script)

UPDATE subscription_plan_settings SET label = 'Premium Nano',           short_label = 'Nano'          WHERE key = 'free';
UPDATE subscription_plan_settings SET label = 'Premium',                short_label = 'Premium'       WHERE key = 'starter';
UPDATE subscription_plan_settings SET label = 'Premium',                short_label = 'Premium'       WHERE key = 'premium';
UPDATE subscription_plan_settings SET label = 'Family Premium',         short_label = 'Family'        WHERE key = 'family_premium';
UPDATE subscription_plan_settings SET label = 'Premium — 6 Months',    short_label = '6-Month'       WHERE key = 'standard_6month';
UPDATE subscription_plan_settings SET label = 'Premium — Annual',       short_label = 'Annual'        WHERE key = 'standard_annual';
UPDATE subscription_plan_settings SET label = 'Family Premium — Annual',short_label = 'Family Annual' WHERE key = 'family_annual';
