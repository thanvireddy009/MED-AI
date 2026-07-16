const pool = require('./config/db');
const fs = require('fs');
const path = require('path');

async function setup() {
    try {
        const schema = fs.readFileSync(path.join(__dirname, 'config/schema.sql'), 'utf8');
        await pool.query(schema);
        console.log('✓ Database tables created successfully');
        process.exit(0);
    } catch (err) {
        console.error('✗ Error creating tables:', err.message);
        process.exit(1);
    }
}

setup();
