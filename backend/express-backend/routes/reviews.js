const express = require('express');
const router = express.Router();
const pool = require('../config/db');

// GET review history for a document
router.get('/:documentId', async (req, res) => {
    try {
        const result = await pool.query(
            'SELECT * FROM review_history WHERE document_id = $1 ORDER BY reviewed_at DESC',
            [req.params.documentId]
        );
        res.json(result.rows);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// GET all review history
router.get('/', async (req, res) => {
    try {
        const result = await pool.query(
            `SELECT rh.*, d.file_name 
             FROM review_history rh 
             JOIN documents d ON rh.document_id = d.id 
             ORDER BY rh.reviewed_at DESC`
        );
        res.json(result.rows);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

module.exports = router;
