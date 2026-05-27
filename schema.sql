CREATE DATABASE IF NOT EXISTS diffuserinter;
USE diffuserinter;

CREATE TABLE IF NOT EXISTS event_entry (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    browser_name VARCHAR(50),
    scenario_id  VARCHAR(500),
    corpus       VARCHAR(500),

    event_type   ENUM('interaction', 'corpus'),

    corpus_type  ENUM(
        'csp',               
        'samesite',          
        'sandbox',           
        'coop',             
        'permission-policy',
        'referrer-policy',   
        'hsts',              
        'x-frame-options'    
    ),
    leak         VARCHAR(500),
    violation    VARCHAR(500),
    interaction  VARCHAR(255) NULL,
    timestamp    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
