CREATE TABLE IF NOT EXISTS service_artists (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS service_releases (
    id BIGSERIAL PRIMARY KEY,
    artist_id BIGINT NOT NULL REFERENCES service_artists(id),
    title TEXT NOT NULL,
    title_key TEXT NOT NULL,
    released_on DATE NOT NULL,
    upc TEXT,
    UNIQUE (artist_id, title_key, released_on)
);
