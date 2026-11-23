CREATE TABLE IF NOT EXISTS players (
    id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{32}$'),
    name text NOT NULL DEFAULT '',
    role text CHECK (role IN ('farmer', 'citizen')),
    coins bigint NOT NULL DEFAULT 0 CHECK (coins >= 0),
    energy integer NOT NULL DEFAULT 60 CHECK (energy BETWEEN 0 AND 100),
    soil_health integer NOT NULL DEFAULT 100 CHECK (soil_health BETWEEN 0 AND 100),
    food_produced bigint NOT NULL DEFAULT 0,
    food_eaten bigint NOT NULL DEFAULT 0,
    coins_earned_work bigint NOT NULL DEFAULT 0,
    coins_spent_soil bigint NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS food_lots (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    farmer_id text NOT NULL REFERENCES players(id),
    quantity bigint NOT NULL CHECK (quantity > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS players_dashboard_order
    ON players (role, lower(name), id) WHERE role IS NOT NULL;

-- Durable idempotency records survive a Redis failure after SQL commit.
CREATE TABLE IF NOT EXISTS challenge_results (
    challenge_id text PRIMARY KEY,
    player_id text NOT NULL REFERENCES players(id),
    outcome text NOT NULL CHECK (outcome IN ('completed', 'cancelled')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS food_purchases (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    citizen_id text NOT NULL REFERENCES players(id),
    farmer_id text NOT NULL REFERENCES players(id),
    quantity integer NOT NULL DEFAULT 1 CHECK (quantity = 1),
    price bigint NOT NULL CHECK (price > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);
