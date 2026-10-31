-- Existing schema v1 upgrade. The application checks column existence on both backends.
-- Old rows were created using the initial default timezone (Asia/Tokyo).
ALTER TABLE memories ADD COLUMN IF NOT EXISTS timezone VARCHAR NOT NULL DEFAULT 'Asia/Tokyo';
INSERT INTO schema_versions(version) VALUES (2) ON CONFLICT DO NOTHING;
