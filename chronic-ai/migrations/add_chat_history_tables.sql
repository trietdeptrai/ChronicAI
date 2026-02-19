-- ============================================
-- Chat History Tables
-- Persistent chat history for doctor and patient AI chat
-- ============================================

-- ============================================
-- 1. Chat Conversations
-- Groups related messages together
-- ============================================
CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_type VARCHAR(20) NOT NULL CHECK (conversation_type IN ('doctor', 'patient')),
    user_id UUID NOT NULL,  -- references doctors.id or patients.id depending on type
    title VARCHAR(500),      -- auto-generated from first message
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. Chat Messages
-- Individual messages within a conversation
-- ============================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',  -- attachments, mentioned_patients, safety_score, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

-- Conversations
CREATE INDEX IF NOT EXISTS idx_chat_conversations_type_user ON chat_conversations(conversation_type, user_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_updated ON chat_conversations(updated_at DESC);

-- Messages
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at ASC);

-- ============================================
-- TRIGGER for updated_at on conversations
-- ============================================
-- Reuses the existing update_updated_at_column() function from setup_db.sql
CREATE TRIGGER update_chat_conversations_updated_at
    BEFORE UPDATE ON chat_conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE chat_conversations IS 'Groups of related AI chat messages for doctors and patients';
COMMENT ON TABLE chat_messages IS 'Individual messages in AI chat conversations';
