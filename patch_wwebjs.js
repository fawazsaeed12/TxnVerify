/**
 * TxnVerify AI - Universal Robust Patch for whatsapp-web.js Media Decryption
 * Replaces Message.prototype.downloadMedia with full asynchronous download resolution,
 * mediaBlob direct extraction, and proxy-based QPL decryption.
 */

const fs = require('fs');
const path = require('path');

const messageFile = path.join(__dirname, 'node_modules', 'whatsapp-web.js', 'src', 'structures', 'Message.js');

if (fs.existsSync(messageFile)) {
    let content = fs.readFileSync(messageFile, 'utf8');

    const targetRegex = /async downloadMedia\(\) \{[\s\S]*?\n    \/\*\*\n     \* Deletes a message/;

    const replacement = `async downloadMedia() {
        if (!this.hasMedia) {
            return undefined;
        }

        try {
            const result = await this.client.pupPage.evaluate(async (msgId) => {
                try {
                    const collections = window.require('WAWebCollections');
                    const msg = collections?.Msg?.get(msgId) ||
                        (await collections?.Msg?.getMessagesById([msgId]))?.messages?.[0];

                    if (!msg || !msg.mediaData || msg.mediaData.mediaStage === 'REUPLOADING') {
                        return null;
                    }

                    // 1. Wait for media resolution if in fetching stage
                    if (msg.mediaData.mediaStage !== 'RESOLVED') {
                        try {
                            await msg.downloadMedia({ downloadEvenIfExpensive: true, rmrReason: 1 });
                        } catch (_) {}

                        for (let i = 0; i < 25; i++) {
                            if (msg.mediaData.mediaStage === 'RESOLVED') break;
                            if (msg.mediaData.mediaStage && msg.mediaData.mediaStage.includes('ERROR')) break;
                            await new Promise(r => setTimeout(r, 200));
                        }
                    }

                    // 2. Direct Blob extraction if available
                    if (msg.mediaData && msg.mediaData.mediaBlob) {
                        try {
                            const blob = msg.mediaData.mediaBlob._blob || msg.mediaData.mediaBlob;
                            if (blob && typeof blob.arrayBuffer === 'function') {
                                const buffer = await blob.arrayBuffer();
                                const bytes = new Uint8Array(buffer);
                                let binary = '';
                                for (let i = 0; i < bytes.byteLength; i++) {
                                    binary += String.fromCharCode(bytes[i]);
                                }
                                const b64 = btoa(binary);
                                if (b64 && b64.length > 500) {
                                    return {
                                        data: b64,
                                        mimetype: msg.mimetype || 'image/jpeg',
                                        filename: msg.filename || 'payment_receipt.jpg',
                                        filesize: msg.size
                                    };
                                }
                            }
                        } catch (_) {}
                    }

                    // 3. Fallback to downloadAndMaybeDecrypt with dynamic Proxy
                    try {
                        const mockQpl = new Proxy({}, { get: () => () => mockQpl });
                        const decryptedMedia = await window
                            .require('WAWebDownloadManager')
                            .downloadManager.downloadAndMaybeDecrypt({
                                directPath: msg.directPath,
                                encFilehash: msg.encFilehash,
                                filehash: msg.filehash,
                                mediaKey: msg.mediaKey,
                                mediaKeyTimestamp: msg.mediaKeyTimestamp,
                                type: msg.type,
                                signal: new AbortController().signal,
                                downloadQpl: mockQpl,
                            });

                        const data = await window.WWebJS.arrayBufferToBase64Async(decryptedMedia);
                        return {
                            data,
                            mimetype: msg.mimetype,
                            filename: msg.filename,
                            filesize: msg.size,
                        };
                    } catch (_) {}

                    return null;
                } catch (evalErr) {
                    return null;
                }
            }, this.id._serialized).catch(() => null);

            if (!result || !result.data) return undefined;
            return new MessageMedia(
                result.mimetype,
                result.data,
                result.filename,
                result.filesize,
            );
        } catch (e) {
            return undefined;
        }
    }

    /**
     * Deletes a message`;

    if (content.match(targetRegex)) {
        content = content.replace(targetRegex, replacement);
        fs.writeFileSync(messageFile, content, 'utf8');
        console.log('[Patch] Successfully applied high-resolution async media download patch to Message.js');
    } else {
        console.log('[Patch] Target method signature not matched or already up to date.');
    }
} else {
    console.warn('[Patch] whatsapp-web.js not found in node_modules.');
}
