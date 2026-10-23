/**
 * TxnVerify AI - Universal Patch for whatsapp-web.js Media Decryption
 * 1. Replaces static mockQpl with Proxy to absorb any internal Meta QPL metrics calls.
 * 2. Safely wraps msg.downloadMedia in try/catch to prevent evaluation crash 'r'.
 * 3. Gracefully returns undefined on media failure so gateway thumbnail fallback triggers cleanly.
 */

const fs = require('fs');
const path = require('path');

const messageFile = path.join(__dirname, 'node_modules', 'whatsapp-web.js', 'src', 'structures', 'Message.js');

if (fs.existsSync(messageFile)) {
    let content = fs.readFileSync(messageFile, 'utf8');
    let modified = false;

    // 1. Patch mockQpl with dynamic Proxy
    if (content.includes('addAnnotations: function')) {
        content = content.replace(/const mockQpl = \{[\s\S]*?addAnnotations[\s\S]*?\};/, 'const mockQpl = new Proxy({}, { get: () => () => mockQpl });');
        modified = true;
    }

    // 2. Wrap msg.downloadMedia in try/catch
    if (content.includes('await msg.downloadMedia({') && !content.includes('try { await msg.downloadMedia({')) {
        content = content.replace(
            /await msg\.downloadMedia\(\{[\s\S]*?\}\);/,
            'try { await msg.downloadMedia({ downloadEvenIfExpensive: true, rmrReason: 1 }); } catch (_) {}'
        );
        modified = true;
    }

    // 3. Prevent throw e in downloadMedia catch block
    if (content.includes('if (e.status && e.status === 404) return undefined;\n                throw e;')) {
        content = content.replace(
            'if (e.status && e.status === 404) return undefined;\n                throw e;',
            'return undefined;'
        );
        modified = true;
    }

    // 4. Wrap pupPage.evaluate in outer catch to absorb browser evaluation rejection 'r'
    if (content.includes('}, this.id._serialized);') && !content.includes('}, this.id._serialized).catch(() => undefined);')) {
        content = content.replace(
            '}, this.id._serialized);',
            '}, this.id._serialized).catch(() => undefined);'
        );
        modified = true;
    }

    if (modified) {
        fs.writeFileSync(messageFile, content, 'utf8');
        console.log('[Patch] Applied comprehensive media decryption fixes to whatsapp-web.js Message.js');
    } else {
        console.log('[Patch] whatsapp-web.js Message.js is up to date.');
    }
} else {
    console.warn('[Patch] whatsapp-web.js not found in node_modules.');
}
