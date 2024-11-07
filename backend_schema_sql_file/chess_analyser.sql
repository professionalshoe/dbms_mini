-- Create the database
CREATE DATABASE chess_analyzer;
USE chess_analyzer;

-- Create the 'users' table
CREATE TABLE users (
    player_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Create the 'win_log' table
CREATE TABLE win_log (
    player_id INT,
    white_win INT DEFAULT 0,
    black_win INT DEFAULT 0,
    no_of_draws INT DEFAULT 0,
    FOREIGN KEY (player_id) REFERENCES users(player_id)
);

-- Create the 'game_data' table
CREATE TABLE game_data (
	id int AUTO_INCREMENT PRIMARY KEY,
    game_id VARCHAR(50) unique,
    white_player VARCHAR(50),
    black_player VARCHAR(50),
    white_result VARCHAR(20),
    black_result VARCHAR(20),
    moves TEXT
);

-- Create the 'saved_games' table
CREATE TABLE saved_games (
    save_id INT AUTO_INCREMENT PRIMARY KEY,
    player_id INT,
    chess_com_game_id VARCHAR(50),
    FOREIGN KEY (player_id) REFERENCES users(player_id),
    FOREIGN KEY (chess_com_game_id) REFERENCES game_data(game_id)
);

-- Display the tables
SHOW TABLES;

use chess_analyzer;
DELIMITER //

CREATE TRIGGER delete_game_data
BEFORE DELETE ON game_data
FOR EACH ROW
BEGIN
    -- Temporarily disable foreign key checks
    SET FOREIGN_KEY_CHECKS = 0;

    -- Delete the related record in saved_games
	DELETE FROM saved_games WHERE chess_com_game_id = (SELECT game_id FROM game_data WHERE id = OLD.id);
    -- Re-enable foreign key checks
    SET FOREIGN_KEY_CHECKS = 1;
END//

DELIMITER ;
