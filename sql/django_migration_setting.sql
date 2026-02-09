SELECT CONSTRAINT_NAME
    INTO @fk_name
    FROM information_schema.KEY_COLUMN_USAGE
 WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'token_blacklist_outstandingtoken'
     AND REFERENCED_TABLE_NAME = 'auth_user'
     AND REFERENCED_COLUMN_NAME = 'id'
 LIMIT 1;

SET @s = CONCAT('ALTER TABLE `token_blacklist_outstandingtoken` DROP FOREIGN KEY `', @fk_name, '`;');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
