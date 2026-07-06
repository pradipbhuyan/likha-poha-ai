-- Migration: Add stream column to profiles for Grade 11/12 students
-- Streams: PCM | PCB | PCMB | Commerce | Humanities
-- Run in Supabase SQL editor (primary DB — profiles table)

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS stream text
CHECK (stream IS NULL OR stream IN ('PCM', 'PCB', 'PCMB', 'Commerce', 'Humanities'));

COMMENT ON COLUMN profiles.stream IS
'Academic stream for Grade 11/12 students. NULL for all other grades/roles.
Values: PCM (Physics+Chemistry+Maths), PCB (Physics+Chemistry+Biology),
PCMB (all four), Commerce, Humanities';
