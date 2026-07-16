const { Pool } = require('pg');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');

// Load .env locally if it exists (ignored on Railway — env vars set in dashboard)
const envPath = path.join(__dirname, '../../../.env');
if (fs.existsSync(envPath)) {
    dotenv.config({ path: envPath });
}

const pool = new Pool({
    connectionString: process.env.NEON_CONNECTION_STRING,
    ssl: { rejectUnauthorized: false }
});

module.exports = pool;
