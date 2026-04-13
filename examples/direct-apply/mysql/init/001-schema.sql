CREATE TABLE IF NOT EXISTS service_artists (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    name_key VARCHAR(255) NOT NULL,
    UNIQUE KEY uq_service_artists_name_key (name_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS service_releases (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    artist_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    title_key VARCHAR(255) NOT NULL,
    released_on DATE NOT NULL,
    upc VARCHAR(64),
    CONSTRAINT fk_service_releases_artist FOREIGN KEY (artist_id) REFERENCES service_artists(id),
    UNIQUE KEY uq_service_releases_natural (artist_id, title_key, released_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
