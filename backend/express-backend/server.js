const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');

// Load .env locally if it exists (ignored on Railway — env vars set in dashboard)
const envPath = path.join(__dirname, '../../../.env');
const fs = require('fs');
if (fs.existsSync(envPath)) {
    dotenv.config({ path: envPath });
}

const app = express();
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/documents', require('./routes/documents'));
app.use('/api/reviews', require('./routes/reviews'));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
