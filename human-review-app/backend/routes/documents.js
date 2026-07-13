const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');
const pool = require('../config/db');

// Setup upload directory
const uploadDir = path.join(__dirname, '../uploads');
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });

const storage = multer.diskStorage({
    destination: (req, file, cb) => cb(null, uploadDir),
    filename: (req, file, cb) => cb(null, `${uuidv4()}-${file.originalname}`)
});
const upload = multer({ storage, fileFilter: (req, file, cb) => {
    cb(null, file.mimetype === 'application/pdf');
}});

// GET all documents
router.get('/', async (req, res) => {
    try {
        const result = await pool.query(
            'SELECT id, file_name, upload_date, status, review_notes FROM documents ORDER BY upload_date DESC'
        );
        res.json(result.rows);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// GET single document
router.get('/:id', async (req, res) => {
    try {
        const result = await pool.query('SELECT * FROM documents WHERE id = $1', [req.params.id]);
        if (!result.rows.length) return res.status(404).json({ error: 'Document not found' });
        res.json(result.rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// POST upload PDF
router.post('/upload', upload.single('pdf'), async (req, res) => {
    try {
        if (!req.file) return res.status(400).json({ error: 'No PDF file uploaded' });

        const id = uuidv4();
        const result = await pool.query(
            'INSERT INTO documents (id, file_name, file_path, status) VALUES ($1, $2, $3, $4) RETURNING *',
            [id, req.file.originalname, req.file.path, 'pending']
        );
        res.json(result.rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// PUT update extracted data
router.put('/:id/data', async (req, res) => {
    try {
        const { extracted_data, validated_data } = req.body;
        const result = await pool.query(
            'UPDATE documents SET extracted_data = $1, validated_data = $2 WHERE id = $3 RETURNING *',
            [extracted_data, validated_data, req.params.id]
        );
        res.json(result.rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// PUT approve document
router.put('/:id/approve', async (req, res) => {
    try {
        const { notes, updated_data } = req.body;

        // Save to review history
        const doc = await pool.query('SELECT * FROM documents WHERE id = $1', [req.params.id]);
        await pool.query(
            'INSERT INTO review_history (document_id, action, previous_data, updated_data, notes) VALUES ($1, $2, $3, $4, $5)',
            [req.params.id, 'approved', doc.rows[0].extracted_data, updated_data || doc.rows[0].extracted_data, notes]
        );

        const result = await pool.query(
            'UPDATE documents SET status = $1, review_notes = $2, validated_data = $3 WHERE id = $4 RETURNING *',
            ['approved', notes, updated_data || doc.rows[0].extracted_data, req.params.id]
        );
        res.json(result.rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// PUT reject document
router.put('/:id/reject', async (req, res) => {
    try {
        const { notes } = req.body;

        const doc = await pool.query('SELECT * FROM documents WHERE id = $1', [req.params.id]);
        await pool.query(
            'INSERT INTO review_history (document_id, action, previous_data, updated_data, notes) VALUES ($1, $2, $3, $4, $5)',
            [req.params.id, 'rejected', doc.rows[0].extracted_data, null, notes]
        );

        const result = await pool.query(
            'UPDATE documents SET status = $1, review_notes = $2 WHERE id = $3 RETURNING *',
            ['rejected', notes, req.params.id]
        );
        res.json(result.rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// DELETE document
router.delete('/:id', async (req, res) => {
    try {
        await pool.query('DELETE FROM review_history WHERE document_id = $1', [req.params.id]);
        await pool.query('DELETE FROM documents WHERE id = $1', [req.params.id]);
        res.json({ message: 'Document deleted' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

module.exports = router;

// POST load extracted data from llm_extracted_data.json by filename
router.post('/:id/load-extracted', async (req, res) => {
    try {
        const path = require('path');
        const fs = require('fs');
        const jsonPath = path.join(__dirname, '../../../llm_extracted_data.json');
        
        if (!fs.existsSync(jsonPath)) {
            return res.status(404).json({ error: 'llm_extracted_data.json not found' });
        }

        const doc = await pool.query('SELECT file_name FROM documents WHERE id = $1', [req.params.id]);
        if (!doc.rows.length) return res.status(404).json({ error: 'Document not found' });

        const fileName = doc.rows[0].file_name;
        const allData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
        const match = allData.find((d) => d.file_name === fileName);

        if (!match) {
            return res.status(404).json({ error: `No extracted data found for ${fileName}` });
        }

        const result = await pool.query(
            'UPDATE documents SET extracted_data = $1, status = $2 WHERE id = $3 RETURNING *',
            [JSON.stringify(match), 'reviewed', req.params.id]
        );
        res.json(result.rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// POST load extracted data from llm_extracted_data.json by filename
router.post('/:id/load-extracted', async (req, res) => {
    try {
        const path = require('path');
        const fs = require('fs');
        const jsonPath = path.join(__dirname, '../../../llm_extracted_data.json');
        
        if (!fs.existsSync(jsonPath)) {
            return res.status(404).json({ error: 'llm_extracted_data.json not found' });
        }

        const doc = await pool.query('SELECT file_name FROM documents WHERE id = $1', [req.params.id]);
        if (!doc.rows.length) return res.status(404).json({ error: 'Document not found' });

        const fileName = doc.rows[0].file_name;
        const allData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
        const match = allData.find((d) => d.file_name === fileName);

        if (!match) {
            return res.status(404).json({ error: `No extracted data found for ${fileName}` });
        }

        const result = await pool.query(
            'UPDATE documents SET extracted_data = $1, status = $2 WHERE id = $3 RETURNING *',
            [JSON.stringify(match), 'reviewed', req.params.id]
        );
        res.json(result.rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

router.post('/:id/load-extracted', async (req, res) => {
    try {
        const path = require('path');
        const fs = require('fs');
        const jsonPath = path.join(__dirname, '../../../llm_extracted_data.json');
        if (!fs.existsSync(jsonPath)) return res.status(404).json({ error: 'llm_extracted_data.json not found' });
        const doc = await pool.query('SELECT file_name FROM documents WHERE id = $1', [req.params.id]);
        if (!doc.rows.length) return res.status(404).json({ error: 'Document not found' });
        const fileName = doc.rows[0].file_name;
        const allData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
        const match = allData.find((d) => d.file_name === fileName);
        if (!match) return res.status(404).json({ error: `No extracted data found for ${fileName}` });
        const result = await pool.query(
            'UPDATE documents SET extracted_data = $1, status = $2 WHERE id = $3 RETURNING *',
            [JSON.stringify(match), 'reviewed', req.params.id]
        );
        res.json(result.rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

router.post('/:id/load-extracted', async (req, res) => {
    try {
        const path = require('path');
        const fs = require('fs');
        const jsonPath = path.join(__dirname, '../../../llm_extracted_data.json');
        if (!fs.existsSync(jsonPath)) return res.status(404).json({ error: 'llm_extracted_data.json not found' });
        const doc = await pool.query('SELECT file_name FROM documents WHERE id = $1', [req.params.id]);
        if (!doc.rows.length) return res.status(404).json({ error: 'Document not found' });
        const fileName = doc.rows[0].file_name;
        const allData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
        const match = allData.find((d) => d.file_name === fileName);
        if (!match) return res.status(404).json({ error: `No extracted data found for ${fileName}` });
        const result = await pool.query(
            'UPDATE documents SET extracted_data = $1, status = $2 WHERE id = $3 RETURNING *',
            [JSON.stringify(match), 'reviewed', req.params.id]
        );
        res.json(result.rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});
