-- Add avatar column to profiles table
-- Run this in Supabase SQL Editor

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS avatar TEXT;
