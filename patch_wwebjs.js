/**
 * TxnVerify AI - Patch for whatsapp-web.js QPL Metrics Error
 * Replaces incomplete mockQpl object with a universal Proxy to prevent
 * internal 'r' / 'addAnnotations' / 'markerPoint' evaluation crashes on WhatsApp Web.
 */

const fs = require('fs');
const path = require('path');

const messageFile = path.join(__dirname, 'node_modules', 'whatsapp-web.js', 'src', 'structures', 'Message.js');

if (fs.existsSync(messageFile)) {
    let content = fs.readFileSync(messageFile, 'utf8');
    const proxyMock = 'const mockQpl = new Proxy({}, { get: () => () => mockQpl });';

    if (content.includes('addAnnotations: function')) {
        content = content.replace(/const mockQpl = \{[\s\S]*?addAnnotations[\s\S]*?\};/, proxyMock);
        fs.writeFileSync(messageFile, content, 'utf8');
        console.log('[Patch] Successfully applied mockQpl Proxy patch to whatsapp-web.js Message.js');
    } else {
        console.log('[Patch] whatsapp-web.js Message.js already contains QPL Proxy patch.');
    }
} else {
    console.warn('[Patch] whatsapp-web.js not found in node_modules.');
}
