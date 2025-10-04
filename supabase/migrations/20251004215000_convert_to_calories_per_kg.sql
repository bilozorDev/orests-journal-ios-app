-- Convert food nutrition from calories_per_container to calories_per_kg

-- First, add the new column
ALTER TABLE pet_foods ADD COLUMN calories_per_kg DOUBLE PRECISION;

-- Convert existing data to calories per kg
-- Formula: calories_per_kg = (calories_per_container / container_size_in_grams) * 1000
UPDATE pet_foods
SET calories_per_kg = CASE
    -- Convert container_size to grams based on unit, then calculate calories per kg
    WHEN container_size_unit = 'g' THEN (calories_per_container / container_size) * 1000
    WHEN container_size_unit = 'oz' THEN (calories_per_container / (container_size * 28.3495)) * 1000
    WHEN container_size_unit = 'kg' THEN (calories_per_container / (container_size * 1000)) * 1000
    WHEN container_size_unit = 'lb' THEN (calories_per_container / (container_size * 453.592)) * 1000
    ELSE (calories_per_container / container_size) * 1000 -- fallback to grams
END;

-- Make the new column NOT NULL after data conversion
ALTER TABLE pet_foods ALTER COLUMN calories_per_kg SET NOT NULL;

-- Drop the old column
ALTER TABLE pet_foods DROP COLUMN calories_per_container;

-- Rename the new column to match Swift model (keeping snake_case for database)
-- calories_per_kg is already the correct name
