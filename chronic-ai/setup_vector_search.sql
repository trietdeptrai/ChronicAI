-- Vector Similarity Search Function for RAG
-- Run this in Supabase SQL Editor after setup_db.sql

CREATE OR REPLACE FUNCTION search_patient_records(
    query_embedding vector(768),
    patient_uuid UUID,
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    record_id UUID,
    chunk_content TEXT,
    chunk_index INT,
    similarity FLOAT,
    record_type TEXT,
    record_title TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        re.id,
        re.record_id,
        re.chunk_content,
        re.chunk_index,
        (1 - (re.embedding <=> query_embedding))::FLOAT AS similarity,
        mr.record_type::TEXT,
        mr.title::TEXT AS record_title,
        re.created_at
    FROM record_embeddings re
    JOIN medical_records mr ON re.record_id = mr.id
    WHERE mr.patient_id = patient_uuid
    AND (1 - (re.embedding <=> query_embedding)) > match_threshold
    ORDER BY re.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION search_patient_records TO authenticated;
GRANT EXECUTE ON FUNCTION search_patient_records TO anon;

COMMENT ON FUNCTION search_patient_records IS 
'Vector similarity search for patient medical records using pgvector cosine distance';
