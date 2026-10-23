/**
 * TxnVerify AI - WhatsApp Gateway Service
 * Built with Node.js, Express, and whatsapp-web.js.
 * Handles client initialization, QR code generation, incoming media webhooks,
 * and automated transaction verification replies.
 */

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const QRCode = require('qrcode');
const axios = require('axios');
const { Client, LocalAuth } = require('whatsapp-web.js');

const app = express();
const PORT = process.env.WHATSAPP_PORT || 3001;
const PYTHON_WEBHOOK_URL = process.env.PYTHON_WEBHOOK_URL || 'http://127.0.0.1:8000/webhook/whatsapp';

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Gateway state
let client = null;
let clientStatus = 'INITIALIZING'; // DISCONNECTED, SCAN_QR, AUTHENTICATED, READY, STOPPED
let currentQrRaw = null;
let currentQrDataUrl = null;
let pairedInfo = null;
let lastError = null;

/**
 * Initialize whatsapp-web.js client with Puppeteer settings.
 */
function initWhatsAppClient() {
    try {
        console.log('[WhatsApp Gateway] Initializing client...');
        clientStatus = 'INITIALIZING';
        currentQrRaw = null;
        currentQrDataUrl = null;
        lastError = null;

        client = new Client({
            authStrategy: new LocalAuth({
                dataPath: './.wwebjs_auth'
            }),
            puppeteer: {
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            }
        });

        client.on('qr', async (qr) => {
            console.log('[WhatsApp Gateway] 📸 QR Code received. Generating Data URL...');
            currentQrRaw = qr;
            clientStatus = 'SCAN_QR';
            try {
                currentQrDataUrl = await QRCode.toDataURL(qr, {
                    width: 350,
                    margin: 2,
                    color: {
                        dark: '#0f172a',
                        light: '#ffffff'
                    }
                });
            } catch (err) {
                console.error('[WhatsApp Gateway] Failed to render QR to Data URL:', err);
            }
        });

        client.on('authenticated', () => {
            console.log('[WhatsApp Gateway] 🔐 Client authenticated successfully!');
            clientStatus = 'AUTHENTICATED';
            currentQrRaw = null;
            currentQrDataUrl = null;
        });

        client.on('auth_failure', (msg) => {
            console.error('[WhatsApp Gateway] ❌ Auth failure:', msg);
            clientStatus = 'AUTH_FAILURE';
            lastError = msg;
        });

        client.on('ready', () => {
            console.log('[WhatsApp Gateway] 🚀 WhatsApp client is READY and listening for messages!');
            clientStatus = 'READY';
            currentQrRaw = null;
            currentQrDataUrl = null;
            try {
                pairedInfo = {
                    pushname: client.info?.pushname || 'User',
                    wid: client.info?.wid?._serialized || 'Unknown',
                    platform: client.info?.platform || 'Unknown'
                };
            } catch (e) {
                pairedInfo = { pushname: 'Connected Device' };
            }
        });

        client.on('disconnected', (reason) => {
            console.warn('[WhatsApp Gateway] ⚠️ WhatsApp client disconnected:', reason);
            clientStatus = 'DISCONNECTED';
            currentQrRaw = null;
            currentQrDataUrl = null;
            pairedInfo = null;
        });

        // Incoming message listener: catches images/screenshots
        client.on('message', async (msg) => {
            console.log(`[WhatsApp Gateway] 📩 Received message from: ${msg.from} | Type: ${msg.type} | HasMedia: ${msg.hasMedia}`);

            if (msg.hasMedia) {
                try {
                    console.log(`[WhatsApp Gateway] 📥 Downloading media from ${msg.from}...`);
                    const media = await msg.downloadMedia();

                    if (!media) {
                        console.warn('[WhatsApp Gateway] Media download returned empty.');
                        return;
                    }

                    // Only forward image types to the Python processing pipeline
                    if (media.mimetype && media.mimetype.startsWith('image/')) {
                        console.log(`[WhatsApp Gateway] 🔄 Forwarding screenshot (${media.mimetype}) to Python pipeline at ${PYTHON_WEBHOOK_URL}...`);

                        const payload = {
                            from: msg.from,
                            sender_name: msg._data?.notifyName || msg.from,
                            body: msg.body || '',
                            timestamp: msg.timestamp,
                            mimetype: media.mimetype,
                            data: media.data, // base64 encoded image string
                            filename: media.filename || 'payment_receipt.jpg'
                        };

                        axios.post(PYTHON_WEBHOOK_URL, payload, { timeout: 75000 })
                            .then(res => {
                                console.log(`[WhatsApp Gateway] ✅ Pipeline response for ${msg.from}:`, res.data?.status || 'OK');
                            })
                            .catch(err => {
                                console.error(`[WhatsApp Gateway] ❌ Error forwarding to Python webhook: ${err.message}`);
                            });
                    } else {
                        console.log(`[WhatsApp Gateway] Ignored non-image media type: ${media.mimetype}`);
                    }
                } catch (err) {
                    console.error('[WhatsApp Gateway] Error processing incoming media:', err);
                }
            }
        });

        client.initialize().catch(err => {
            console.error('[WhatsApp Gateway] client.initialize() error:', err.message);
            clientStatus = 'ERROR';
            lastError = err.message;
        });

    } catch (e) {
        console.error('[WhatsApp Gateway] Exception in initWhatsAppClient:', e);
        clientStatus = 'ERROR';
        lastError = e.message;
    }
}

// -------------------------------------------------------------
// REST API Endpoints for Streamlit Frontend & Python Engine
// -------------------------------------------------------------

/**
 * Health check & status
 */
app.get('/status', (req, res) => {
    res.json({
        status: clientStatus,
        has_qr: !!currentQrDataUrl,
        paired_info: pairedInfo,
        error: lastError,
        timestamp: new Date().toISOString()
    });
});

/**
 * Retrieve QR Code as Data URL or JSON
 */
app.get('/qr', (req, res) => {
    if (currentQrDataUrl) {
        res.json({
            status: clientStatus,
            qr_data_url: currentQrDataUrl,
            raw_code: currentQrRaw
        });
    } else {
        res.json({
            status: clientStatus,
            qr_data_url: null,
            message: clientStatus === 'READY' ? 'Client is already connected' : 'QR code not ready yet'
        });
    }
});

/**
 * Send a WhatsApp text reply back to a customer/sender
 */
app.post('/send-message', async (req, res) => {
    const { to, message } = req.body;

    if (!to || !message) {
        return res.status(400).json({ error: 'Missing required parameters: to, message' });
    }

    if (clientStatus !== 'READY' || !client) {
        console.warn(`[WhatsApp Gateway] Cannot send message: client status is ${clientStatus}`);
        return res.status(503).json({
            error: 'WhatsApp client is not connected',
            status: clientStatus
        });
    }

    try {
        // Ensure chatId has @c.us or @g.us suffix
        let chatId = to;
        if (!chatId.includes('@')) {
            // Clean phone digits
            const digits = to.replace(/\D/g, '');
            chatId = `${digits}@c.us`;
        }

        console.log(`[WhatsApp Gateway] 📤 Sending message to ${chatId}...`);
        await client.sendMessage(chatId, message);
        console.log(`[WhatsApp Gateway] ✅ Message sent successfully to ${chatId}`);

        res.json({ success: true, to: chatId, timestamp: new Date().toISOString() });
    } catch (err) {
        console.error(`[WhatsApp Gateway] ❌ Failed to send message to ${to}:`, err.message);
        res.status(500).json({ error: err.message });
    }
});

/**
 * Start or restart the WhatsApp gateway client
 */
app.post('/start', (req, res) => {
    if (client && (clientStatus === 'READY' || clientStatus === 'SCAN_QR')) {
        return res.json({ message: 'Client already running', status: clientStatus });
    }
    initWhatsAppClient();
    res.json({ message: 'Client initialization triggered', status: clientStatus });
});

/**
 * Stop or destroy the WhatsApp gateway client
 */
app.post('/stop', async (req, res) => {
    try {
        if (client) {
            console.log('[WhatsApp Gateway] Stopping WhatsApp client...');
            await client.destroy();
            client = null;
        }
        clientStatus = 'STOPPED';
        currentQrDataUrl = null;
        currentQrRaw = null;
        res.json({ message: 'Client stopped', status: clientStatus });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

/**
 * Simulate an incoming receipt message (for hackathon judge live testing)
 */
app.post('/simulate-incoming', async (req, res) => {
    const { from, data, mimetype, filename } = req.body;
    if (!data) {
        return res.status(400).json({ error: 'Missing base64 image data' });
    }

    const payload = {
        from: from || '15551234567@c.us',
        sender_name: 'Judge Demo Tester',
        body: 'Simulated payment receipt',
        timestamp: Math.floor(Date.now() / 1000),
        mimetype: mimetype || 'image/jpeg',
        data: data,
        filename: filename || 'receipt.jpg'
    };

    try {
        const response = await axios.post(PYTHON_WEBHOOK_URL, payload, { timeout: 75000 });
        res.json({ success: true, forward_result: response.data });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Start Express Server
app.listen(PORT, () => {
    console.log(`=======================================================`);
    console.log(`TxnVerify AI - WhatsApp Gateway listening on port ${PORT}`);
    console.log(`Forwarding incoming screenshots to: ${PYTHON_WEBHOOK_URL}`);
    console.log(`=======================================================`);

    // Auto-start WhatsApp client on boot if AUTO_START is not explicitly disabled
    if (process.env.AUTO_START !== 'false') {
        initWhatsAppClient();
    }
});
