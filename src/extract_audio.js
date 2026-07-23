import fs from 'fs';
import path from 'path';

/**
 * HDAR Audio Extraction & Renaming Tool (Node.js).
 * 
 * Scans the brain directory for uploaded voice recordings (.img files)
 * and copies them to the workspace renamed as standard playable .webm files.
 */

const BRAIN_DIR = '/Users/alep/.gemini/antigravity-ide/brain/4fde26ea-29fb-4024-bb1c-40ff99dc0b53';
const OUTPUT_DIR = './audio_recordings';

function extractAudio() {
    console.log('[*] Scanning brain folder for audio assets...');

    if (!fs.existsSync(BRAIN_DIR)) {
        console.error(`[-] Brain folder not found: ${BRAIN_DIR}`);
        process.exit(1);
    }

    if (!fs.existsSync(OUTPUT_DIR)) {
        fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }

    const files = fs.readdirSync(BRAIN_DIR);
    const audioFiles = files.filter(f => f.startsWith('uploaded_media') && f.endsWith('.img'));

    console.log(`[*] Found ${audioFiles.length} uploaded audio recordings.`);

    // Sort files by their timestamps in the name to keep them in chronological order
    audioFiles.sort((a, b) => {
        const matchA = a.match(/\d+/);
        const matchB = b.match(/\d+/);
        if (matchA && matchB) {
            return parseInt(matchA[0]) - parseInt(matchB[0]);
        }
        return a.localeCompare(b);
    });

    const mapping = [];

    audioFiles.forEach((file, index) => {
        const srcPath = path.join(BRAIN_DIR, file);
        const destName = `recording_${index + 1}.webm`;
        const destPath = path.join(OUTPUT_DIR, destName);

        fs.copyFileSync(srcPath, destPath);
        console.log(`[+] Exported: ${file} ➔ ${destPath}`);
        mapping.push({
            original: file,
            exported: destName,
            absolute_path: path.resolve(destPath)
        });
    });

    // Write a mapping index JSON file
    fs.writeFileSync(
        path.join(OUTPUT_DIR, 'audio_index.json'),
        JSON.stringify(mapping, null, 2)
    );
    console.log('[*] Audio extraction completed successfully.');
}

extractAudio();
