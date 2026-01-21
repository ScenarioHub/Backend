
create database scenariohub;
use scenariohub;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  email VARCHAR(255) NOT NULL,
  pass_hash VARCHAR(255) NULL,
  name VARCHAR(100) NOT NULL,
  initials VARCHAR(10) NOT NULL,
  provider_id VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP NULL DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_email (email)
);

CREATE TABLE IF NOT EXISTS scenarios (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  owner_id BIGINT UNSIGNED NOT NULL,
  file_url VARCHAR(255) NOT NULL,
  video_url TEXT NOT NULL,
  file_format VARCHAR(50) NOT NULL,
  file_version VARCHAR(50) NOT NULL,
  file_size BIGINT NOT NULL,
  code_snippet TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_scenarios_owner_id (owner_id),
  CONSTRAINT fk_scenarios_owner
    FOREIGN KEY (owner_id)
    REFERENCES users (id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS posts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  scenario_id BIGINT UNSIGNED NOT NULL,
  uploader_id BIGINT UNSIGNED NOT NULL,
  title VARCHAR(255) NOT NULL,
  template_desc TEXT NULL,
  description TEXT NULL,
  view_count INT NOT NULL DEFAULT 0,
  download_count INT NOT NULL DEFAULT 0,
  like_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_posts_scenario_id (scenario_id),
  KEY idx_posts_uploader_id (uploader_id),
  CONSTRAINT fk_posts_scenario
    FOREIGN KEY (scenario_id)
    REFERENCES scenarios (id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_posts_uploader
    FOREIGN KEY (uploader_id)
    REFERENCES users (id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS likes (
  user_id BIGINT UNSIGNED NOT NULL,
  scenario_id BIGINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, scenario_id),
  CONSTRAINT fk_likes_user
    FOREIGN KEY (user_id)
    REFERENCES users (id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_likes_scenario
    FOREIGN KEY (scenario_id)
    REFERENCES scenarios (id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_tags_name (name)
);

CREATE TABLE IF NOT EXISTS scenario_tags (
  scenario_id BIGINT UNSIGNED NOT NULL,
  tag_id BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (scenario_id, tag_id),
  CONSTRAINT fk_scenario_tags_scenario
    FOREIGN KEY (scenario_id)
    REFERENCES scenarios (id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_scenario_tags_tag
    FOREIGN KEY (tag_id)
    REFERENCES tags (id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS maps (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `map_name` VARCHAR(45) NOT NULL,
  `description` TEXT NULL,
  `file_url` VARCHAR(255) NOT NULL,
  `img_url` VARCHAR(255) NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `map_name_UNIQUE` (`map_name` ASC) VISIBLE);
