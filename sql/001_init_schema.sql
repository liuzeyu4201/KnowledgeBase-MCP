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

CREATE TABLE IF NOT EXISTS kb_import_task (
    id BIGSERIAL PRIMARY KEY,
    task_uid VARCHAR(36) NOT NULL UNIQUE,
    task_type VARCHAR(64) NOT NULL DEFAULT 'document_import_batch',
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    priority INT NOT NULL DEFAULT 50,
    cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
    idempotency_key VARCHAR(128) UNIQUE,
    request_id VARCHAR(128),
    operator VARCHAR(128),
    trace_id VARCHAR(128),
    total_items INT NOT NULL DEFAULT 0,
    pending_items INT NOT NULL DEFAULT 0,
    running_items INT NOT NULL DEFAULT 0,
    success_items INT NOT NULL DEFAULT 0,
    failed_items INT NOT NULL DEFAULT 0,
    canceled_items INT NOT NULL DEFAULT 0,
    progress_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
    attempt_count INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    lease_token VARCHAR(64),
    lease_expires_at TIMESTAMP,
    heartbeat_at TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_kb_import_task_status_priority
    ON kb_import_task (status, priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_kb_import_task_cancel_requested ON kb_import_task (cancel_requested);
CREATE INDEX IF NOT EXISTS idx_kb_import_task_lease_expires_at ON kb_import_task (lease_expires_at);
CREATE INDEX IF NOT EXISTS idx_kb_import_task_request_id ON kb_import_task (request_id);

CREATE TABLE IF NOT EXISTS kb_staged_file (
    id BIGSERIAL PRIMARY KEY,
    staged_file_uid VARCHAR(36) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'uploaded',
    storage_backend VARCHAR(32) NOT NULL DEFAULT 'local',
    storage_uri VARCHAR(1024) NOT NULL,
    file_name VARCHAR(256) NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    file_size BIGINT NOT NULL,
    file_sha256 VARCHAR(64) NOT NULL,
    upload_completed_at TIMESTAMP,
    expires_at TIMESTAMP,
    consumed_at TIMESTAMP,
    last_error TEXT,
    linked_document_id BIGINT REFERENCES kb_document(id),
    linked_task_id BIGINT REFERENCES kb_import_task(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_kb_staged_file_status
    ON kb_staged_file (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kb_staged_file_expires_at ON kb_staged_file (expires_at);
CREATE INDEX IF NOT EXISTS idx_kb_staged_file_file_sha256 ON kb_staged_file (file_sha256);
CREATE INDEX IF NOT EXISTS idx_kb_staged_file_mime_type ON kb_staged_file (mime_type);
CREATE INDEX IF NOT EXISTS idx_kb_staged_file_deleted_at ON kb_staged_file (deleted_at);

CREATE TABLE IF NOT EXISTS kb_import_task_item (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES kb_import_task(id),
    item_no INT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    priority INT NOT NULL DEFAULT 50,
    category_id BIGINT NOT NULL,
    title VARCHAR(256) NOT NULL,
    file_name VARCHAR(256) NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    staged_file_id BIGINT NOT NULL REFERENCES kb_staged_file(id),
    file_sha256 VARCHAR(64),
    document_id BIGINT,
    document_uid VARCHAR(36),
    attempt_count INT NOT NULL DEFAULT 0,
    lease_token VARCHAR(64),
    lease_expires_at TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_kb_import_task_item_task_item_no UNIQUE (task_id, item_no)
);

CREATE INDEX IF NOT EXISTS idx_kb_import_task_item_status
    ON kb_import_task_item (status, priority DESC, id ASC);
CREATE INDEX IF NOT EXISTS idx_kb_import_task_item_task_id ON kb_import_task_item (task_id);
CREATE INDEX IF NOT EXISTS idx_kb_import_task_item_document_id ON kb_import_task_item (document_id);
CREATE INDEX IF NOT EXISTS idx_kb_import_task_item_staged_file_id ON kb_import_task_item (staged_file_id);

CREATE TABLE IF NOT EXISTS kb_storage_gc_task (
    id BIGSERIAL PRIMARY KEY,
    resource_type VARCHAR(32) NOT NULL,
    resource_id BIGINT,
    storage_backend VARCHAR(32) NOT NULL,
    storage_uri VARCHAR(1024) NOT NULL,
    action VARCHAR(32) NOT NULL DEFAULT 'delete',
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    retry_count INT NOT NULL DEFAULT 0,
    max_retry_count INT NOT NULL DEFAULT 20,
    lease_token VARCHAR(64),
    lease_expires_at TIMESTAMP,
    next_retry_at TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_kb_storage_gc_task_status_next_retry_at
    ON kb_storage_gc_task (status, next_retry_at, id);
CREATE INDEX IF NOT EXISTS idx_kb_storage_gc_task_resource
    ON kb_storage_gc_task (resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_kb_storage_gc_task_lease_expires_at
    ON kb_storage_gc_task (lease_expires_at);
