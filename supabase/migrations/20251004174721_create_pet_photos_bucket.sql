-- Create storage bucket for pet photos
INSERT INTO storage.buckets (id, name, public)
VALUES ('pet-photos', 'pet-photos', true)
ON CONFLICT (id) DO NOTHING;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Public can view pet photos" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can upload pet photos" ON storage.objects;
DROP POLICY IF EXISTS "Users can update their own photos" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete their own photos" ON storage.objects;

-- Policy: Anyone can view pet photos (public bucket)
CREATE POLICY "Public can view pet photos"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'pet-photos');

-- Policy: Authenticated users can upload pet photos
CREATE POLICY "Authenticated users can upload pet photos"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'pet-photos' AND
        auth.role() = 'authenticated'
    );

-- Policy: Users can update their own uploaded photos
CREATE POLICY "Users can update their own photos"
    ON storage.objects FOR UPDATE
    USING (
        bucket_id = 'pet-photos' AND
        auth.uid() = owner::uuid
    );

-- Policy: Users can delete their own uploaded photos
CREATE POLICY "Users can delete their own photos"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'pet-photos' AND
        auth.uid() = owner::uuid
    );
