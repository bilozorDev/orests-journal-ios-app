-- Seed file for test data
-- This will run after migrations when you run: supabase db reset

-- Create test user with known credentials
-- Password: testpassword123
-- Email: test@example.com
INSERT INTO auth.users (
    id,
    instance_id,
    email,
    encrypted_password,
    email_confirmed_at,
    created_at,
    updated_at,
    raw_app_meta_data,
    raw_user_meta_data,
    is_super_admin,
    role,
    aud,
    confirmation_token,
    recovery_token,
    email_change_token_new,
    email_change
) VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    '00000000-0000-0000-0000-000000000000',
    'test@example.com',
    -- This is bcrypt hash of 'testpassword123'
    '$2a$10$gZkZmvQFLGlYvfQYPj5Mj.eCRrNWvNhQPSqKvLqMZqTzK1p6qUqGC',
    NOW(),
    NOW(),
    NOW(),
    '{"provider":"email","providers":["email"]}',
    '{}',
    FALSE,
    'authenticated',
    'authenticated',
    '',
    '',
    '',
    ''
);

-- Create identity for the user
INSERT INTO auth.identities (
    id,
    user_id,
    provider_id,
    identity_data,
    provider,
    last_sign_in_at,
    created_at,
    updated_at
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    jsonb_build_object('sub', '00000000-0000-0000-0000-000000000001', 'email', 'test@example.com'),
    'email',
    NOW(),
    NOW(),
    NOW()
);

-- Create family for test user
INSERT INTO families (id, name, created_by, created_at)
VALUES (
    '10000000-0000-0000-0000-000000000001'::uuid,
    'Test Family',
    '00000000-0000-0000-0000-000000000001'::uuid,
    NOW()
);

-- Add test user to family
INSERT INTO family_members (id, family_id, user_id, role, joined_at)
VALUES (
    '20000000-0000-0000-0000-000000000001'::uuid,
    '10000000-0000-0000-0000-000000000001'::uuid,
    '00000000-0000-0000-0000-000000000001'::uuid,
    'owner',
    NOW()
);

-- Create test pet
INSERT INTO pets (id, family_id, name, kind, current_weight, created_at)
VALUES (
    '30000000-0000-0000-0000-000000000001'::uuid,
    '10000000-0000-0000-0000-000000000001'::uuid,
    'Orest',
    'dog',
    25.0,
    NOW()
);

-- Create some test health categories
INSERT INTO pet_health_categories (id, pet_id, name, name_normalized, created_by, created_at)
VALUES
    (
        '40000000-0000-0000-0000-000000000001'::uuid,
        '30000000-0000-0000-0000-000000000001'::uuid,
        'Asthma Attack',
        'asthma attack',
        '00000000-0000-0000-0000-000000000001'::uuid,
        NOW()
    ),
    (
        '40000000-0000-0000-0000-000000000002'::uuid,
        '30000000-0000-0000-0000-000000000001'::uuid,
        'Vet Visit',
        'vet visit',
        '00000000-0000-0000-0000-000000000001'::uuid,
        NOW()
    ),
    (
        '40000000-0000-0000-0000-000000000003'::uuid,
        '30000000-0000-0000-0000-000000000001'::uuid,
        'Vaccination',
        'vaccination',
        '00000000-0000-0000-0000-000000000001'::uuid,
        NOW()
    );

-- Create some test health events
INSERT INTO pet_health_events (id, category_id, occurred_at, notes, created_by, created_at)
VALUES
    (
        '50000000-0000-0000-0000-000000000001'::uuid,
        '40000000-0000-0000-0000-000000000001'::uuid,
        NOW() - INTERVAL '2 days',
        'Had trouble breathing after running. Used inhaler.',
        '00000000-0000-0000-0000-000000000001'::uuid,
        NOW()
    ),
    (
        '50000000-0000-0000-0000-000000000002'::uuid,
        '40000000-0000-0000-0000-000000000002'::uuid,
        NOW() - INTERVAL '1 week',
        'Annual checkup. Everything looks good!',
        '00000000-0000-0000-0000-000000000001'::uuid,
        NOW()
    ),
    (
        '50000000-0000-0000-0000-000000000003'::uuid,
        '40000000-0000-0000-0000-000000000003'::uuid,
        NOW() - INTERVAL '6 months',
        'Rabies vaccine updated',
        '00000000-0000-0000-0000-000000000001'::uuid,
        NOW()
    );

-- Create test food
INSERT INTO pet_foods (id, family_id, name, category, calories_per_kg, container_size, container_size_unit, created_by, created_at)
VALUES (
    '60000000-0000-0000-0000-000000000001'::uuid,
    '10000000-0000-0000-0000-000000000001'::uuid,
    'Premium Dog Food',
    'dry',
    3500,
    5,
    'kg',
    '00000000-0000-0000-0000-000000000001'::uuid,
    NOW()
);

-- Create calorie goal
INSERT INTO pet_calorie_goals (id, pet_id, daily_calories, effective_from, notes, created_by, created_at)
VALUES (
    '70000000-0000-0000-0000-000000000001'::uuid,
    '30000000-0000-0000-0000-000000000001'::uuid,
    800,
    NOW() - INTERVAL '1 month',
    'Based on vet recommendation',
    '00000000-0000-0000-0000-000000000001'::uuid,
    NOW()
);

-- Create some feeding records
INSERT INTO pet_feedings (id, pet_id, food_id, fed_by, fed_at, amount, amount_unit, calories, created_at)
VALUES
    (
        '80000000-0000-0000-0000-000000000001'::uuid,
        '30000000-0000-0000-0000-000000000001'::uuid,
        '60000000-0000-0000-0000-000000000001'::uuid,
        '00000000-0000-0000-0000-000000000001'::uuid,
        NOW() - INTERVAL '8 hours',
        200,
        'g',
        700,
        NOW()
    ),
    (
        '80000000-0000-0000-0000-000000000002'::uuid,
        '30000000-0000-0000-0000-000000000001'::uuid,
        '60000000-0000-0000-0000-000000000001'::uuid,
        '00000000-0000-0000-0000-000000000001'::uuid,
        NOW() - INTERVAL '2 hours',
        100,
        'g',
        350,
        NOW()
    );
