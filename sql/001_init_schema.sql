CREATE TABLE IF NOT EXISTS kb_category (
    id BIGSERIAL PRIMARY KEY,
    category_code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL UNIQUE,
    description VARCHAR(512),
    status SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_kb_category_status ON kb_category (status);
CREATE INDEX IF NOT EXISTS idx_kb_category_deleted_at ON kb_category (deleted_at);

CREATE TABLE IF NOT EXISTS kb_document (
    id BIGSERIAL PRIMARY KEY,
    document_uid VARCHAR(36) NOT NULL UNIQUE,
    category_id BIGINT NOT NULL REFERENCES kb_category(id),
    title VARCHAR(256) NOT NULL,
    source_type VARCHAR(32) NOT NULL DEFAULT 'pdf',
    file_name VARCHAR(256) NOT NULL,
    storage_uri VARCHAR(1024) NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    file_size BIGINT NOT NULL,
    file_sha256 VARCHAR(64) NOT NULL,
    parse_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    vector_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    version INT NOT NULL DEFAULT 1,
    chunk_count INT NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_kb_document_category_id ON kb_document (category_id);
CREATE INDEX IF NOT EXISTS idx_kb_document_status ON kb_document (parse_status, vector_status);
CREATE INDEX IF NOT EXISTS idx_kb_document_file_sha256 ON kb_document (file_sha256);
CREATE INDEX IF NOT EXISTS idx_kb_document_deleted_at ON kb_document (deleted_at);

CREATE TABLE IF NOT EXISTS kb_chunk (
    id BIGSERIAL PRIMARY KEY,
    chunk_uid VARCHAR(36) NOT NULL UNIQUE,
    document_id BIGINT NOT NULL REFERENCES kb_document(id),
    chunk_no INT NOT NULL,
    page_no INT,
    char_start INT,
    char_end INT,
    token_count INT,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding_model VARCHAR(128) NOT NULL,
    vector_version INT NOT NULL DEFAULT 1,
    vector_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    metadata_json JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    CONSTRAINT uq_kb_chunk_document_chunk_no UNIQUE (document_id, chunk_no)
);

CREATE INDEX IF NOT EXISTS idx_kb_chunk_document_id ON kb_chunk (document_id);
CREATE INDEX IF NOT EXISTS idx_kb_chunk_vector_status ON kb_chunk (vector_status, vector_version);
CREATE INDEX IF NOT EXISTS idx_kb_chunk_content_hash ON kb_chunk (content_hash);
CREATE INDEX IF NOT EXISTS idx_kb_chunk_deleted_at ON kb_chunk (deleted_at);
