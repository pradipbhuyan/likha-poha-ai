-- ============================================================
-- CONFIRMED CLEANUP: Delete 73 Grade 7 Maths formulas that
-- were incorrectly uploaded as Grade 9 Mathematics.
--
-- These IDs were identified by the STEP 1 SELECT query.
-- All 73 rows confirmed as Grade 7 NCERT content:
--   Integers, Fractions and Decimals, Data Handling,
--   Simple Equations, Lines and Angles, The Triangle and its
--   Properties, Comparing Quantities, Rational Numbers,
--   Perimeter and Area, Algebraic Expressions, Exponents and
--   Powers, Symmetry, Visualising Solid Shapes
--
-- Your original Grade 9 formulas are NOT in this list.
-- This DELETE is safe to run directly.
-- ============================================================

-- STEP 1: Verify count before deleting (should return 73)
SELECT COUNT(*) AS rows_to_delete
FROM formula_sheets
WHERE id IN (
  '5a8046fd-8020-4508-95da-dfeb2310b5d1',
  '5c6aea07-e2fc-4f1a-83b5-a03dcb9503bc',
  'fce828a4-dd23-4da2-b67f-8075fbfc51f8',
  '860cfa3e-ccae-4485-88b3-14087974d5c2',
  'eab6f3bb-055e-45a1-b870-d0b891bc9212',
  '06892277-66ff-4b76-aaf5-a271a8f98617',
  'dac3362d-13ec-458a-bf8a-87f17b3aa519',
  '50fddbf0-9865-40a5-9fb2-309369efe76c',
  '16905c86-a49c-4bf9-8118-47c436635c67',
  'b613c065-ac83-4e18-9bb8-379cd464c60b',
  '35ca0f7c-5802-42ed-b3fa-595fff1ac074',
  'd04e7eeb-865b-42be-8b06-3f0f1346ead5',
  'fa2917d9-2d7d-43fe-b607-8a4ab11a1e74',
  'c0630d4e-471a-43db-ad5e-3803e7ca23f0',
  '5fc6cf42-9b84-41bd-a9a0-4ca449625d4e',
  'eb65f6e9-303f-494b-a3d3-c71718b73fa2',
  'a3b1e05f-7177-4e3e-8a86-716a21647251',
  '89149810-66e4-4d52-bedb-894366b8492a',
  '667bdf4c-8d04-4d66-a756-8c8fa81772d2',
  '54f62592-ff69-4d13-955a-b120d8ab70d6',
  'f1e95638-7992-468d-a2e9-a084ed62b8af',
  '17f56620-8717-44b9-836f-3f0d6fd2eb00',
  '9cec9d7b-d3aa-4097-807e-3d5229f87725',
  '83944cad-b7ce-487d-a025-cee39b6653dc',
  '96cdd919-530d-47b6-b087-423f742bfe24',
  'f5dde12a-bb41-422a-86ad-e264a81b8fdf',
  '5cbe7847-b2fd-4c11-b78b-aaa21564b736',
  'e85d0122-a175-453d-a811-f1172b6683b7',
  'a69620d8-6e79-4478-a930-c35c04db0de0',
  '8bd0d471-1e2f-4880-9263-eb70bd9def77',
  '1e48bc7c-f380-45f4-95dd-c19d4e438419',
  '176796bb-3ba6-49e8-a51b-9a63d17f7927',
  'c44d9dcc-d4c0-404f-869e-0a2dc3b71204',
  '9b45a120-438b-48fb-ac65-c10eaa6a76dd',
  '049accc0-f530-4f86-8bd8-e148afeaeb43',
  '5778ca6d-1b50-4849-9093-212710c7881a',
  '8c23c08e-4c4e-4d4b-a4ba-8d35cb2a4ff4',
  '8603ba84-6bc6-46aa-b9f5-de5358fec716',
  'd07fe969-b94f-4b3c-9ca9-ba6a91cc46a7',
  '476b10b3-e4b3-4c05-9718-04743d76ed01',
  '44dc2a2c-82e4-426d-9799-4cee19f09365',
  '36fdb998-9059-4f92-a829-b082a1c83b60',
  'c3555ac1-c994-4cdb-9a4a-087ade3ab7a1',
  '7d79d197-2f40-4cfe-aaa2-b4b223ae33a2',
  '9c0e4ca8-b56e-4b1e-a9e0-65139293eb17',
  '30ef1cee-1362-441b-84ba-1de6f7d5d1d1',
  '31293de1-b38d-4654-b48f-6401dfc9e86d',
  '3221ef4d-f36e-4b36-b07b-db7007b8bffb',
  '98eb2838-bdf8-4586-b4df-53dce80746af',
  'b1f01d6b-e4c7-4a0c-bc75-4a14d73ed74b',
  '487db374-1a86-4282-8f87-6249040ad65e',
  'e87d87bf-a4f6-497e-b0d9-13276611b795',
  '677be2cf-387f-40ec-b561-2f6beaefade9',
  '40c3d46a-4074-4ac1-9a63-cd6129aadfcd',
  '04c5d1c8-1d3f-4737-84b6-8849503e8a33',
  '9cfd3aac-e46a-4807-b126-aa8a2d00b634',
  '9e4e930c-afb6-4fe2-a8f8-6df9cb0e3610',
  '9f53117d-29b6-4493-90ee-9d9be7496ce0',
  '215c9818-0606-4dc9-8137-b85e09cb4e95',
  '5f0a4477-bef3-48b2-9bed-d539e5a4fcc5',
  '2403b70b-0df0-484c-93ba-209eda90b507',
  '1d55d84a-b201-4390-a19f-9f848c181da6',
  'dc791d5b-f59c-4bc0-8c17-8c1d5cb54a2f',
  '21710d82-c1d9-4acc-a6b7-09b4b29c14ff',
  'fe2cd42c-5571-4dc3-b8e0-eeecbcd6487f',
  'e3b6a6ce-4196-4f9b-a5fc-548b005fbbfc',
  'd5466b32-1e11-4018-9c72-47e07e31bda5',
  '5d7ae69d-fc37-46db-acc5-44c348f5bc6a',
  '700981ee-ff41-44bf-a354-279766bcd4c9',
  '30476b85-cae3-4233-8f95-02ffa73e3c0c',
  'a4879d3c-f4a4-4fcb-86f4-0b1b2f9556d8',
  '3c0eed32-a6bf-45ab-b189-378fa88ab33d'
);

-- ============================================================
-- STEP 2: DELETE — Run this after confirming count = 73 above
-- ============================================================

DELETE FROM formula_sheets
WHERE id IN (
  '5a8046fd-8020-4508-95da-dfeb2310b5d1',
  '5c6aea07-e2fc-4f1a-83b5-a03dcb9503bc',
  'fce828a4-dd23-4da2-b67f-8075fbfc51f8',
  '860cfa3e-ccae-4485-88b3-14087974d5c2',
  'eab6f3bb-055e-45a1-b870-d0b891bc9212',
  '06892277-66ff-4b76-aaf5-a271a8f98617',
  'dac3362d-13ec-458a-bf8a-87f17b3aa519',
  '50fddbf0-9865-40a5-9fb2-309369efe76c',
  '16905c86-a49c-4bf9-8118-47c436635c67',
  'b613c065-ac83-4e18-9bb8-379cd464c60b',
  '35ca0f7c-5802-42ed-b3fa-595fff1ac074',
  'd04e7eeb-865b-42be-8b06-3f0f1346ead5',
  'fa2917d9-2d7d-43fe-b607-8a4ab11a1e74',
  'c0630d4e-471a-43db-ad5e-3803e7ca23f0',
  '5fc6cf42-9b84-41bd-a9a0-4ca449625d4e',
  'eb65f6e9-303f-494b-a3d3-c71718b73fa2',
  'a3b1e05f-7177-4e3e-8a86-716a21647251',
  '89149810-66e4-4d52-bedb-894366b8492a',
  '667bdf4c-8d04-4d66-a756-8c8fa81772d2',
  '54f62592-ff69-4d13-955a-b120d8ab70d6',
  'f1e95638-7992-468d-a2e9-a084ed62b8af',
  '17f56620-8717-44b9-836f-3f0d6fd2eb00',
  '9cec9d7b-d3aa-4097-807e-3d5229f87725',
  '83944cad-b7ce-487d-a025-cee39b6653dc',
  '96cdd919-530d-47b6-b087-423f742bfe24',
  'f5dde12a-bb41-422a-86ad-e264a81b8fdf',
  '5cbe7847-b2fd-4c11-b78b-aaa21564b736',
  'e85d0122-a175-453d-a811-f1172b6683b7',
  'a69620d8-6e79-4478-a930-c35c04db0de0',
  '8bd0d471-1e2f-4880-9263-eb70bd9def77',
  '1e48bc7c-f380-45f4-95dd-c19d4e438419',
  '176796bb-3ba6-49e8-a51b-9a63d17f7927',
  'c44d9dcc-d4c0-404f-869e-0a2dc3b71204',
  '9b45a120-438b-48fb-ac65-c10eaa6a76dd',
  '049accc0-f530-4f86-8bd8-e148afeaeb43',
  '5778ca6d-1b50-4849-9093-212710c7881a',
  '8c23c08e-4c4e-4d4b-a4ba-8d35cb2a4ff4',
  '8603ba84-6bc6-46aa-b9f5-de5358fec716',
  'd07fe969-b94f-4b3c-9ca9-ba6a91cc46a7',
  '476b10b3-e4b3-4c05-9718-04743d76ed01',
  '44dc2a2c-82e4-426d-9799-4cee19f09365',
  '36fdb998-9059-4f92-a829-b082a1c83b60',
  'c3555ac1-c994-4cdb-9a4a-087ade3ab7a1',
  '7d79d197-2f40-4cfe-aaa2-b4b223ae33a2',
  '9c0e4ca8-b56e-4b1e-a9e0-65139293eb17',
  '30ef1cee-1362-441b-84ba-1de6f7d5d1d1',
  '31293de1-b38d-4654-b48f-6401dfc9e86d',
  '3221ef4d-f36e-4b36-b07b-db7007b8bffb',
  '98eb2838-bdf8-4586-b4df-53dce80746af',
  'b1f01d6b-e4c7-4a0c-bc75-4a14d73ed74b',
  '487db374-1a86-4282-8f87-6249040ad65e',
  'e87d87bf-a4f6-497e-b0d9-13276611b795',
  '677be2cf-387f-40ec-b561-2f6beaefade9',
  '40c3d46a-4074-4ac1-9a63-cd6129aadfcd',
  '04c5d1c8-1d3f-4737-84b6-8849503e8a33',
  '9cfd3aac-e46a-4807-b126-aa8a2d00b634',
  '9e4e930c-afb6-4fe2-a8f8-6df9cb0e3610',
  '9f53117d-29b6-4493-90ee-9d9be7496ce0',
  '215c9818-0606-4dc9-8137-b85e09cb4e95',
  '5f0a4477-bef3-48b2-9bed-d539e5a4fcc5',
  '2403b70b-0df0-484c-93ba-209eda90b507',
  '1d55d84a-b201-4390-a19f-9f848c181da6',
  'dc791d5b-f59c-4bc0-8c17-8c1d5cb54a2f',
  '21710d82-c1d9-4acc-a6b7-09b4b29c14ff',
  'fe2cd42c-5571-4dc3-b8e0-eeecbcd6487f',
  'e3b6a6ce-4196-4f9b-a5fc-548b005fbbfc',
  'd5466b32-1e11-4018-9c72-47e07e31bda5',
  '5d7ae69d-fc37-46db-acc5-44c348f5bc6a',
  '700981ee-ff41-44bf-a354-279766bcd4c9',
  '30476b85-cae3-4233-8f95-02ffa73e3c0c',
  'a4879d3c-f4a4-4fcb-86f4-0b1b2f9556d8',
  '3c0eed32-a6bf-45ab-b189-378fa88ab33d'
);

-- ============================================================
-- STEP 3: VERIFY — Run after DELETE to confirm Grade 9 Maths
-- now shows only the correct original Grade 9 formulas.
-- ============================================================

SELECT chapter, COUNT(*) AS formula_count
FROM formula_sheets
WHERE grade = 'Grade 9' AND subject = 'Mathematics'
GROUP BY chapter
ORDER BY chapter;
