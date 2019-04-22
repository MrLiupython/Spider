CREATE TABLE IF NOT EXISTS `news_t` (
    `id` INT AUTO_INCREMENT,
    `title` VARCHAR(16) NOT NULL,
    `url` VARCHAR(64) NOT NULL,
    `type` VARCHAR(16) NOT NULL,
    `publish_time` VARCHAR(32) NOT NULL,
    `article_id` INT NOT NULL,
    `compliance` INT NOT NULL,
    PRIMARY KEY (`id`)
)ENGINE=InnoDB DEFAULT CHARSET=utf8;
