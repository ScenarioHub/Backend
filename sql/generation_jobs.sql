-- generation_jobs.sql
-- Generation job table for asynchronous scenario generation (reduced schema)
-- Assumes database `scenariohub` exists (see init.sql)
drop table generation_jobs;

CREATE TABLE IF NOT EXISTS generation_jobs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_uuid CHAR(36) NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
  description TEXT NOT NULL,
  map_id INT NOT NULL,
  status ENUM('pending','running','failed','done') NOT NULL DEFAULT 'pending',
  scenario_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_generation_jobs_job_uuid (job_uuid),
  KEY idx_generation_jobs_user_id (user_id),
  KEY idx_generation_jobs_status (status),
  -- Note: We intentionally do NOT enforce a foreign key constraint on user_id
  -- because anonymous jobs will use user_id = 0 (no corresponding users row).
  CONSTRAINT fk_generation_jobs_scenario
    FOREIGN KEY (scenario_id)
    REFERENCES scenarios (id)
    ON DELETE SET NULL
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Notes:
-- job_uuid: use a UUID (char 36) for external references to avoid exposing auto-increment ids.
-- This reduced schema intentionally omits progress/message/xosc_path/video_path/created_at/updated_at.
-- If you later need metadata, consider adding columns or a separate job_events table.
