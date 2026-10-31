-- M2 initial schema v1. No data or credentials.
CREATE EXTENSION IF NOT EXISTS vector;


CREATE TABLE IF NOT EXISTS memories (
	id VARCHAR NOT NULL,
	user_id VARCHAR NOT NULL,
	character_id VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	fact TEXT NOT NULL,
	category VARCHAR NOT NULL,
	slot VARCHAR NOT NULL,
	source_message_id VARCHAR NOT NULL,
	source_kind VARCHAR NOT NULL,
	event_date VARCHAR,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITHOUT TIME ZONE,
	importance FLOAT NOT NULL,
	confidence FLOAT NOT NULL,
	version INTEGER NOT NULL,
	embedding VECTOR(768) NOT NULL,
	embedding_version VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE INDEX IF NOT EXISTS ix_memories_status ON memories (status);

CREATE INDEX IF NOT EXISTS ix_memories_character_id ON memories (character_id);

CREATE INDEX IF NOT EXISTS ix_memories_user_id ON memories (user_id);


CREATE TABLE IF NOT EXISTS memory_revisions (
	id VARCHAR NOT NULL,
	user_id VARCHAR NOT NULL,
	memory_id VARCHAR NOT NULL,
	version INTEGER NOT NULL,
	action VARCHAR NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE INDEX IF NOT EXISTS ix_memory_revisions_user_id ON memory_revisions (user_id);


CREATE TABLE IF NOT EXISTS memory_revocations (
	key VARCHAR NOT NULL,
	user_id VARCHAR NOT NULL,
	PRIMARY KEY (key)
)

;

CREATE INDEX IF NOT EXISTS ix_memory_revocations_user_id ON memory_revocations (user_id);


CREATE TABLE IF NOT EXISTS players (
	id VARCHAR NOT NULL,
	token_hash VARCHAR NOT NULL,
	memory_enabled BOOLEAN NOT NULL,
	timezone VARCHAR NOT NULL,
	epoch INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (token_hash)
)

;

CREATE TABLE IF NOT EXISTS schema_versions (version INTEGER PRIMARY KEY);
INSERT INTO schema_versions(version) VALUES (1) ON CONFLICT DO NOTHING;
