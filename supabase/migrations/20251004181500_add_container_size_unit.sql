-- Add container_size_unit column to pet_foods table
ALTER TABLE pet_foods ADD COLUMN container_size_unit TEXT NOT NULL DEFAULT 'g' CHECK (container_size_unit IN ('g', 'oz', 'kg', 'lb'));

-- Rename container_size_grams to container_size for clarity
ALTER TABLE pet_foods RENAME COLUMN container_size_grams TO container_size;

-- Add index for faster queries
CREATE INDEX idx_pet_foods_unit ON pet_foods(container_size_unit);
