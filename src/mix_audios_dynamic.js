import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

/**
 * HDAR Dynamic Audio Superimposition Tool (Node.js).
 * 
 * Mixes all 16 audio recordings simultaneously but dynamically modulates 
 * their volumes over time. Each recording gets a 4-second "peak window" 
 * (volume = 1.0) while all other tracks are ducked to background level (volume = 0.1).
 * This maximizes comprehension and prevents phonetic collisions from making the text unreadable.
 */

const AUDIO_DIR = './audio_recordings';
const OUTPUT_FILE = path.join(AUDIO_DIR, 'dynamic_superimposed_recordings.webm');
const WINDOW_DURATION = 4.0; // Seconds each track remains dominant

function mixAudiosDynamic() {
    console.log('[*] Preparing dynamic audio superimposition...');

    if (!fs.existsSync(AUDIO_DIR)) {
        console.error(`[-] Audio directory not found: ${AUDIO_DIR}`);
        process.exit(1);
    }

    const files = fs.readdirSync(AUDIO_DIR)
        .filter(f => f.startsWith('recording_') && f.endsWith('.webm'))
        .sort((a, b) => {
            const numA = parseInt(a.match(/\d+/)[0]);
            const numB = parseInt(b.match(/\d+/)[0]);
            return numA - numB;
        });

    if (files.length === 0) {
        console.error('[-] No recording files found.');
        process.exit(1);
    }

    console.log(`[*] Found ${files.length} files to mix dynamically.`);

    // Build the ffmpeg command
    const inputs = files.map(f => `-i "${path.join(AUDIO_DIR, f)}"`).join(' ');
    
    // Build volume filters for each input
    let filterString = '';
    files.forEach((_, idx) => {
        const start = idx * WINDOW_DURATION;
        const end = (idx + 1) * WINDOW_DURATION;
        
        // Expression: if t is within the window, volume is 1.0, otherwise duck to 0.1
        filterString += `[${idx}:a]volume='if(between(t,${start},${end}),1.0,0.1)':eval=frame[v${idx}]; `;
    });

    // Mix all volume-adjusted streams
    const mixInputs = files.map((_, idx) => `[v${idx}]`).join('');
    filterString += `${mixInputs}amix=inputs=${files.length}:duration=longest[out]`;

    const ffmpegCmd = `ffmpeg -y ${inputs} -filter_complex "${filterString}" -map "[out]" "${OUTPUT_FILE}"`;

    console.log('[*] Executing ffmpeg dynamic mix command...');
    try {
        execSync(ffmpegCmd, { stdio: 'inherit' });
        console.log(`[+] Success! Dynamic superimposed file created at: ${OUTPUT_FILE}`);
    } catch (error) {
        console.error('[-] Failed to superimpose audio files dynamically:', error.message);
        process.exit(1);
    }
}

mixAudiosDynamic();
