import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

/**
 * HDAR Audio Superimposition Tool (Node.js).
 * 
 * Takes all 16 extracted audio recordings and mixes them simultaneously
 * into a single output file using ffmpeg's amix filter.
 */

const AUDIO_DIR = './audio_recordings';
const OUTPUT_FILE = path.join(AUDIO_DIR, 'superimposed_recordings.webm');

function mixAudios() {
    console.log('[*] Preparing to mix all audio recordings...');

    if (!fs.existsSync(AUDIO_DIR)) {
        console.error(`[-] Audio directory not found: ${AUDIO_DIR}`);
        process.exit(1);
    }

    const files = fs.readdirSync(AUDIO_DIR)
        .filter(f => f.startsWith('recording_') && f.endsWith('.webm'))
        // Sort numerically
        .sort((a, b) => {
            const numA = parseInt(a.match(/\d+/)[0]);
            const numB = parseInt(b.match(/\d+/)[0]);
            return numA - numB;
        });

    if (files.length === 0) {
        console.error('[-] No recording files found in audio_recordings directory.');
        process.exit(1);
    }

    console.log(`[*] Found ${files.length} files to superimpose.`);

    // Build the ffmpeg command inputs
    const inputArgs = files.map(f => `-i "${path.join(AUDIO_DIR, f)}"`).join(' ');

    // Build the amix filter
    const filterArg = `-filter_complex "amix=inputs=${files.length}:duration=longest"`;

    // Complete command
    const ffmpegCmd = `ffmpeg -y ${inputArgs} ${filterArg} "${OUTPUT_FILE}"`;

    console.log('[*] Executing ffmpeg audio mix command...');
    try {
        execSync(ffmpegCmd, { stdio: 'inherit' });
        console.log(`[+] Success! Superimposed file created at: ${OUTPUT_FILE}`);
    } catch (error) {
        console.error('[-] Failed to superimpose audio files:', error.message);
        process.exit(1);
    }
}

mixAudios();
