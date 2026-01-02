USE scenariohub;

DROP VIEW IF EXISTS view_scenario_items;
DROP VIEW IF EXISTS view_scenario_details;
DROP VIEW IF EXISTS view_my_scenarios;
DROP VIEW IF EXISTS view_my_profile;

CREATE VIEW view_scenario_items AS
SELECT
    p.id AS id,
    p.title AS title,
    p.description AS description,
    p.created_at AS createdAt,
    
    -- 작성자 정보 (Users Join)
    u.name AS uploader_name,
    u.initials AS uploader_initials,
    
    -- 통계 정보
    p.download_count AS stats_downloads,
    p.view_count AS stats_views,
    p.like_count AS stats_likes,
    
    -- 태그 (쉼표로 구분된 문자열로 합침 -> 서버 코드에서 배열로 변환 필요)
    -- (MySQL: GROUP_CONCAT / Postgres: STRING_AGG)
    (SELECT GROUP_CONCAT(t.name) 
     FROM scenario_tags st 
     JOIN tags t ON st.tag_id = t.id 
     WHERE st.scenario_id = p.scenario_id) AS tags

FROM posts p
JOIN users u ON p.uploader_id = u.id;

CREATE VIEW view_scenario_details AS
SELECT
    p.id AS id,
    p.title AS title,
    p.description AS description,
    p.created_at AS createdAt,
    
    -- 원본 시나리오 정보 (Scenarios Join)
    s.code_snippet AS code,
    s.file_format AS file_format,
    s.file_version AS file_version,
    s.file_size AS file_size,
    
    -- 통계
    p.download_count AS stats_downloads,
    p.view_count AS stats_views,
    p.like_count AS stats_likes,
    
    -- 작성자 정보
    u.name AS uploader_name,
    u.initials AS uploader_initials,
    u.email AS uploader_email,
    -- (서브쿼리) 이 사람의 총 게시물 수
    (SELECT COUNT(*) FROM posts WHERE uploader_id = u.id) AS uploader_total_scenarios,
    
    -- 태그
    (SELECT GROUP_CONCAT(t.name) 
     FROM scenario_tags st 
     JOIN tags t ON st.tag_id = t.id 
     WHERE st.scenario_id = p.scenario_id) AS tags

FROM posts p
JOIN scenarios s ON p.scenario_id = s.id
JOIN users u ON p.uploader_id = u.id;

CREATE VIEW view_my_scenarios AS
SELECT
    p.id AS id,
    p.uploader_id AS uploader_id, -- 내 글 조회용 필터 조건
    p.title AS title,
    -- 설명 요약 (앞 100자만)
    LEFT(p.description, 100) AS summary,
    p.created_at AS createdAt,
    p.download_count AS downloadCount
FROM posts p;

CREATE VIEW view_my_profile AS
SELECT
    u.id AS id,
    u.email AS email,
    u.name AS name,
    u.initials AS initials,
    u.created_at AS joinedAt,
    -- 내가 올린 게시물 수
    (SELECT COUNT(*) FROM posts WHERE uploader_id = u.id) AS post_count
FROM users u;