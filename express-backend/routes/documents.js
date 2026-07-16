
const express = require('express');

const router = express.Router();

const multer = require('multer');

const path = require('path');

const fs = require('fs');

const { v4: uuidv4 } = require('uuid');

const pool = require('../config/db');
 
const uploadDir = path.join(__dirname, '../uploads');

if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });
 
const storage = multer.diskStorage({

    destination: (req, file, cb) => cb(null, uploadDir),

    filename: (req, file, cb) => cb(null, `${uuidv4()}-${file.originalname}`)

});

const upload = multer({ storage, fileFilter: (req, file, cb) => {

    cb(null, file.mimetype === 'application/pdf');

}});
 
const JSON_PATH = path.join(__dirname, '../../../llm_extracted_data.json');
 
// Helper: write an updated record back into llm_extracted_data.json by file_name

function syncToJsonFile(fileName, updatedData) {

    try {

        if (!fs.existsSync(JSON_PATH)) return false;

        const allData = JSON.parse(fs.readFileSync(JSON_PATH, 'utf8'));

        const idx = allData.findIndex((d) => d.file_name === fileName);

        if (idx === -1) return false;
 
        // Preserve file_name, overwrite everything else with the edited data

        allData[idx] = { ...updatedData, file_name: fileName };
 
        fs.writeFileSync(JSON_PATH, JSON.stringify(allData, null, 4), 'utf8');

        return true;

    } catch (err) {

        console.error('Failed to sync JSON file:', err.message);

        return false;

    }

}
 
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
 
router.get('/approved', async (req, res) => {

    try {

        const result = await pool.query(

            'SELECT id, file_name, upload_date, validated_data FROM documents WHERE status = $1 ORDER BY upload_date DESC',

            ['approved']

        );

        res.json(result.rows);

    } catch (err) {

        res.status(500).json({ error: err.message });

    }

});
 
router.get('/search', async (req, res) => {

    try {

        const { query } = req.query;

        if (!query) return res.json([]);

        const result = await pool.query(

            `SELECT id, file_name, upload_date, status, validated_data, extracted_data

             FROM documents

             WHERE status = 'approved'

             AND (

                 validated_data->'patient_information'->>'full_name' ILIKE $1

                 OR validated_data->'patient_information'->>'patient_identifier' ILIKE $1

                 OR extracted_data->'patient_information'->>'full_name' ILIKE $1

                 OR extracted_data->'patient_information'->>'patient_identifier' ILIKE $1

             )

             ORDER BY upload_date DESC`,

            [`%${query}%`]

        );

        res.json(result.rows);

    } catch (err) {

        res.status(500).json({ error: err.message });

    }

});
 
router.get('/:id', async (req, res) => {

    try {

        const result = await pool.query('SELECT * FROM documents WHERE id = $1', [req.params.id]);

        if (!result.rows.length) return res.status(404).json({ error: 'Document not found' });

        res.json(result.rows[0]);

    } catch (err) {

        res.status(500).json({ error: err.message });

    }

});
 
router.post('/upload', upload.single('pdf'), async (req, res) => {

    try {

        if (!req.file) return res.status(400).json({ error: 'No PDF file uploaded' });

        const id = uuidv4();

        const originalName = req.file.originalname;

        let extractedData = null;

        if (fs.existsSync(JSON_PATH)) {

            const allData = JSON.parse(fs.readFileSync(JSON_PATH, 'utf8'));

            const match = allData.find((d) => d.file_name === originalName);

            if (match) extractedData = match;

        }

        const status = extractedData ? 'reviewed' : 'pending';

        const result = await pool.query(

            'INSERT INTO documents (id, file_name, file_path, status, extracted_data) VALUES ($1, $2, $3, $4, $5) RETURNING *',

            [id, originalName, req.file.path, status, extractedData ? JSON.stringify(extractedData) : null]

        );

        res.json(result.rows[0]);

    } catch (err) {

        res.status(500).json({ error: err.message });

    }

});
 
// PUT update extracted data — now ALSO syncs back to llm_extracted_data.json

router.put('/:id/data', async (req, res) => {

    try {

        const { extracted_data, validated_data } = req.body;
 
        const result = await pool.query(

            'UPDATE documents SET extracted_data = $1, validated_data = $2 WHERE id = $3 RETURNING *',

            [extracted_data, validated_data, req.params.id]

        );
 
        const doc = result.rows[0];

        const synced = syncToJsonFile(doc.file_name, validated_data || extracted_data);
 
        res.json({ ...doc, json_synced: synced });

    } catch (err) {

        res.status(500).json({ error: err.message });

    }

});
 
// PUT approve — also syncs to JSON

router.put('/:id/approve', async (req, res) => {

    try {

        const { notes, updated_data } = req.body;

        const doc = await pool.query('SELECT * FROM documents WHERE id = $1', [req.params.id]);

        const finalData = updated_data || doc.rows[0].extracted_data;
 
        await pool.query(

            'INSERT INTO review_history (document_id, action, previous_data, updated_data, notes) VALUES ($1, $2, $3, $4, $5)',

            [req.params.id, 'approved', doc.rows[0].extracted_data, finalData, notes]

        );

        const result = await pool.query(

            'UPDATE documents SET status = $1, review_notes = $2, validated_data = $3 WHERE id = $4 RETURNING *',

            ['approved', notes, finalData, req.params.id]

        );
 
        const synced = syncToJsonFile(result.rows[0].file_name, finalData);
 
        res.json({ ...result.rows[0], json_synced: synced });

    } catch (err) {

        res.status(500).json({ error: err.message });

    }

});
 
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

