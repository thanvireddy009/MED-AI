CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    upload_date TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'approved', 'rejected')),
    extracted_data JSONB,
    validated_data JSONB,
    review_notes TEXT
);

CREATE TABLE IF NOT EXISTS review_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    action TEXT NOT NULL,
    previous_data JSONB,
    updated_data JSONB,
    reviewer TEXT DEFAULT 'reviewer',
    reviewed_at TIMESTAMP DEFAULT NOW(),
    notes TEXT
);
