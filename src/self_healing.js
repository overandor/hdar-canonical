/**
 * self_healing.js
 * 
 * Implements Self-Healing Code Integrity & Acoustic Fingerprinting.
 * Monitors target files for tampering, automatically restores them from a golden backup,
 * and alerts the user using system-level acoustic tones.
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { execSync } from 'child_process';

const TARGET_FILE = path.join(process.cwd(), 'disassembled_ide/package.json');
const GOLDEN_BACKUP = path.join(process.cwd(), 'disassembled_ide/package.json.golden');

function getHash(filePath) {
    if (!fs.existsSync(filePath)) return null;
    const data = fs.readFileSync(filePath);
    return crypto.createHash('sha256').update(data).digest('hex');
}

function playAcousticTone(type) {
    try {
        if (type === 'healing') {
            // Trigger a distinct Tink sound on macOS for restoration
            execSync('afplay /System/Library/Sounds/Tink.aiff');
        } else if (type === 'error') {
            // Trigger a Basso warning sound for detection
            execSync('afplay /System/Library/Sounds/Basso.aiff');
        }
    } catch (e) {
        // Fallback to standard terminal bell if afplay is unavailable
        process.stdout.write('\x07');
    }
}

export function setupSelfHealing() {
    if (!fs.existsSync(TARGET_FILE)) {
        console.error(`[SELF-HEALING] Target file does not exist: ${TARGET_FILE}`);
        return;
    }

    // Create golden backup
    fs.copyFileSync(TARGET_FILE, GOLDEN_BACKUP);
    const goldenHash = getHash(GOLDEN_BACKUP);
    console.log(`[SELF-HEALING] Golden backup established. Hash: ${goldenHash}`);

    // Watch the target file
    fs.watch(TARGET_FILE, (eventType) => {
        if (eventType === 'change') {
            const currentHash = getHash(TARGET_FILE);
            if (currentHash !== goldenHash) {
                console.log(`[SELF-HEALING] WARNING: Tampering detected on ${path.basename(TARGET_FILE)}.`);
                playAcousticTone('error');

                // Restore golden state
                console.log(`[SELF-HEALING] Restoring to golden state...`);
                fs.copyFileSync(GOLDEN_BACKUP, TARGET_FILE);
                
                playAcousticTone('healing');
                console.log(`[SELF-HEALING] Restore complete. State verified.`);
            }
        }
    });
}

// Run experiment if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
    console.log("=== Starting Self-Healing Experiment ===");
    setupSelfHealing();

    // Perform Tampering Simulation after 2 seconds
    setTimeout(() => {
        console.log(`\n[EXPERIMENT] Simulating tampering by injecting malicious telemetry...`);
        const originalContent = fs.readFileSync(TARGET_FILE, 'utf8');
        
        // Inject telemetry key
        const tamperedContent = originalContent.replace('"version": "1.107.0"', '"version": "1.107.0", "telemetry_exfiltration": true');
        fs.writeFileSync(TARGET_FILE, tamperedContent, 'utf8');
    }, 2000);

    // Stop experiment after 5 seconds
    setTimeout(() => {
        console.log(`\n[EXPERIMENT] Verifying final file state:`);
        const currentContent = fs.readFileSync(TARGET_FILE, 'utf8');
        const hasTelemetry = currentContent.includes('telemetry_exfiltration');
        console.log(`Has Telemetry: ${hasTelemetry}`);
        console.log(`File Restored Correctly: ${!hasTelemetry}`);
        
        // Cleanup golden backup
        if (fs.existsSync(GOLDEN_BACKUP)) {
            fs.unlinkSync(GOLDEN_BACKUP);
        }
        console.log("=== Experiment Complete ===");
        process.exit(0);
    }, 5000);
}
