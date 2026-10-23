/**
 * TxnVerify AI - WhatsApp Gateway Service
 * Built with Node.js, Express, and whatsapp-web.js.
 * Handles client initialization, QR code generation, incoming media webhooks,
 * and automated transaction verification replies.
 */

require('dotenv').config();
require('./patch_wwebjs.js');
const express = require('express');
const cors = require('cors');
const QRCode = require('qrcode');
const axios = require('axios');
const path = require('path');
const fs = require('fs');
const { Client, LocalAuth } = require('whatsapp-web.js');

// Top-level crash guards to prevent Windows SQLite file lock crashes (EBUSY)
process.on('uncaughtException', (err) => {
    console.warn('[WhatsApp Gateway] Handled uncaughtException:', err.message);
    if (err.code === 'EBUSY' || (err.message && err.message.includes('EBUSY'))) {
        console.warn('[WhatsApp Gateway] Windows file lock on cleanup gracefully bypassed.');
    }
});

process.on('unhandledRejection', (reason) => {
    console.warn('[WhatsApp Gateway] Handled unhandledRejection:', reason);
});

const app = express();
const PORT = process.env.WHATSAPP_PORT || 3001;
const PYTHON_WEBHOOK_URL = process.env.PYTHON_WEBHOOK_URL || 'http://127.0.0.1:8000/webhook/whatsapp';

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Gateway state
let client = null;
let clientStatus = 'INITIALIZING'; // DISCONNECTED, SCAN_QR, AUTHENTICATED, READY, STOPPED, ERROR
let currentQrRaw = null;
let currentQrDataUrl = null;
let pairedInfo = null;
let lastError = null;
let isInitializing = false;

/**
 * Initialize whatsapp-web.js client with Puppeteer settings.
 */
function initWhatsAppClient() {
    if (isInitializing) {
        console.log('[WhatsApp Gateway] Initialization already in progress, skipping duplicate call.');
        return;
    }
    isInitializing = true;

    try {
        console.log('[WhatsApp Gateway] Initializing client...');
        clientStatus = 'INITIALIZING';
        currentQrRaw = null;
        currentQrDataUrl = null;
        lastError = null;

        if (client) {
            try {
                client.destroy().catch(() => {});
            } catch (e) {}
            client = null;
        }

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
                    '--disable-gpu',
                    '--disable-extensions'
                ]
            }
        });

        client.on('qr', async (qr) => {
            console.log('[WhatsApp Gateway] 📸 QR Code received. Generating Data URL...');
            currentQrRaw = qr;
            clientStatus = 'SCAN_QR';
            isInitializing = false;
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
            isInitializing = false;
        });

        client.on('auth_failure', (msg) => {
            console.error('[WhatsApp Gateway] ❌ Auth failure:', msg);
            clientStatus = 'AUTH_FAILURE';
            lastError = msg;
            isInitializing = false;
        });

        client.on('ready', () => {
            console.log('[WhatsApp Gateway] 🚀 WhatsApp client is READY and listening for messages!');
            clientStatus = 'READY';
            currentQrRaw = null;
            currentQrDataUrl = null;
            isInitializing = false;
            try {
                pairedInfo = {
                    pushname: client.info?.pushname || 'User',
                    wid: client.info?.wid?._serialized || 'Connected',
                    platform: client.info?.platform || 'WhatsApp Web'
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
            isInitializing = false;
        });

        // Incoming message listener: catches images/screenshots
        client.on('message', async (msg) => {
            console.log(`[WhatsApp Gateway] 📩 Received message from: ${msg.from} | Type: ${msg.type} | HasMedia: ${msg.hasMedia}`);

            if (msg.hasMedia) {
                try {
                    console.log(`[WhatsApp Gateway] 📥 Fetching media from ${msg.from}...`);
                    
                    let media = null;
                    // Progressive retry loop with small backoff (gives WhatsApp Web time to buffer/decrypt)
                    for (let attempt = 1; attempt <= 3; attempt++) {
                        try {
                            // Wait 800ms before first attempt, 1500ms on retries
                            await new Promise(res => setTimeout(res, attempt === 1 ? 800 : 1500));
                            media = await msg.downloadMedia();
                            if (media && media.data) {
                                console.log(`[WhatsApp Gateway] ✅ Media downloaded successfully on attempt ${attempt}`);
                                break;
                            }
                        } catch (downloadErr) {
                            console.warn(`[WhatsApp Gateway] Attempt ${attempt}/3 download notice: ${downloadErr.message || downloadErr}`);
                        }
                    }

                    // Fallback to thumbnail body data if full media download was blocked by WhatsApp Web
                    if (!media && msg._data && msg._data.body && typeof msg._data.body === 'string' && msg._data.body.length > 50) {
                        console.log('[WhatsApp Gateway] ℹ️ Using embedded message thumbnail data as fallback');
                        media = {
                            data: msg._data.body,
                            mimetype: msg._data.mimetype || 'image/jpeg',
                            filename: 'receipt.jpg'
                        };
                    }

                    if (!media || !media.data) {
                        console.warn('[WhatsApp Gateway] ⚠️ Could not resolve media buffer from WhatsApp message.');
                        return;
                    }

                    // Only forward image types to the Python processing pipeline
                    if (media.mimetype && media.mimetype.startsWith('image/')) {
                        console.log(`[WhatsApp Gateway] 🔄 Forwarding screenshot (${media.mimetype}, ${Math.round(media.data.length / 1024)} KB) to Python pipeline at ${PYTHON_WEBHOOK_URL}...`);

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
                    console.error('[WhatsApp Gateway] Error in media message handler:', err.message || err);
                }
            }
        });

        client.initialize().catch(err => {
            console.warn('[WhatsApp Gateway] client.initialize() error caught:', err.message);
            clientStatus = 'ERROR';
            lastError = err.message;
            isInitializing = false;
        });

    } catch (e) {
        console.warn('[WhatsApp Gateway] Exception in initWhatsAppClient caught:', e.message);
        clientStatus = 'ERROR';
        lastError = e.message;
        isInitializing = false;
    }
}

// -------------------------------------------------------------
// REST API Endpoints for Streamlit Frontend & Python Engine
// -------------------------------------------------------------

app.get('/status', (req, res) => {
    res.json({
        status: clientStatus,
        has_qr: !!currentQrDataUrl,
        paired_info: pairedInfo,
        error: lastError,
        timestamp: new Date().toISOString()
    });
});

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
        let chatId = to;
        if (!chatId.includes('@')) {
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

app.post('/start', (req, res) => {
    if (client && (clientStatus === 'READY' || clientStatus === 'SCAN_QR')) {
        return res.json({ message: 'Client already active', status: clientStatus });
    }
    isInitializing = false;
    initWhatsAppClient();
    res.json({ message: 'Client initialization triggered', status: clientStatus });
});

app.post('/stop', async (req, res) => {
    try {
        if (client) {
            console.log('[WhatsApp Gateway] Stopping WhatsApp client...');
            await client.destroy().catch(() => {});
            client = null;
        }
        clientStatus = 'STOPPED';
        currentQrDataUrl = null;
        currentQrRaw = null;
        isInitializing = false;
        res.json({ message: 'Client stopped', status: clientStatus });
    } catch (err) {
        res.json({ message: 'Client stopped with notice', status: 'STOPPED' });
    }
});

// Start Express Server
app.listen(PORT, () => {
    console.log(`=======================================================`);
    console.log(`TxnVerify AI - WhatsApp Gateway listening on port ${PORT}`);
    console.log(`Forwarding incoming screenshots to: ${PYTHON_WEBHOOK_URL}`);
    console.log(`=======================================================`);

    if (process.env.AUTO_START !== 'false') {
        initWhatsAppClient();
    }
});
