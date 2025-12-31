
-- Add custom_ratings column to compliance_ratings table for storing additional fields
ALTER TABLE compliance_ratings 
ADD COLUMN IF NOT EXISTS custom_ratings JSONB DEFAULT '{}';

-- Create index on custom_ratings for better query performance
CREATE INDEX IF NOT EXISTS idx_compliance_ratings_custom_ratings 
ON compliance_ratings USING GIN (custom_ratings);

-- Add comment for documentation
COMMENT ON COLUMN compliance_ratings.custom_ratings IS 'JSONB storage for additional rating fields in key-value format';

