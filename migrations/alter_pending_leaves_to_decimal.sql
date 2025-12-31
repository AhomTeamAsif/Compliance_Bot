-- Migration: Change pending_leaves column from INTEGER to DECIMAL(5,1)
-- This allows storing half-day leaves (e.g., 10.5 days)
-- DECIMAL(5,1) means: 5 total digits with 1 decimal place (e.g., 9999.9)

-- Step 1: Alter the column type
ALTER TABLE users
ALTER COLUMN pending_leaves TYPE DECIMAL(5,1);

-- Step 2: Add a comment to document the change
COMMENT ON COLUMN users.pending_leaves IS 'Number of pending leave days (supports half-days with 0.5 increments)';

-- Verification query (optional - run this to check the change)
-- SELECT column_name, data_type, numeric_precision, numeric_scale
-- FROM information_schema.columns
-- WHERE table_name = 'users' AND column_name = 'pending_leaves';
