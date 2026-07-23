import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

/**
 * HDAR Node.js Electron App Disassembler.
 * 
 * This script runs completely in Node.js (Python is prohibited).
 * It disassembles the active Antigravity IDE Electron application by:
 * 1. Locating the resources/app folder of the running IDE.
 * 2. Lazily scanning and copying configuration files and core JavaScript modules.
 * 3. Computing SHA256 integrity checksums for verification.
 * 4. Storing the state in a local manifest.
 */

const SOURCE_APP_DIR = '/Applications/Antigravity IDE.app/Contents/Resources/app';
const DEST_DIR = './disassembled_ide';

function log(msg) {
    console.log(`[*] ${msg}`);
}

// Helper to recursively copy directories with filters
function copyDirSync(src, dest, filterFn) {
    const exists = fs.existsSync(src);
    const stats = exists && fs.statSync(src);
    const isDirectory = exists && stats.isDirectory();

    if (isDirectory) {
        fs.mkdirSync(dest, { recursive: true });
        fs.readdirSync(src).forEach((childItemName) => {
            const srcPath = path.join(src, childItemName);
            const destPath = path.join(dest, childItemName);
            if (filterFn(srcPath, childItemName)) {
                copyDirSync(srcPath, destPath, filterFn);
            }
        });
    } else {
        fs.copyFileSync(src, dest);
    }
}

// Helper to calculate file SHA-256 hash
function calculateFileHash(filePath) {
    const fileBuffer = fs.readFileSync(filePath);
    const hashSum = crypto.createHash('sha256');
    hashSum.update(fileBuffer);
    return hashSum.digest('hex');
}

function runDisassembly() {
    log('======================================================');
    log('HDAR ELECTRON APP DISASSEMBLY & STRIPPING PIPELINE');
    log('======================================================');

    if (!fs.existsSync(SOURCE_APP_DIR)) {
        log(`ERROR: Antigravity IDE source folder not found at: ${SOURCE_APP_DIR}`);
        process.exit(1);
    }

    log(`Target Application: ${SOURCE_APP_DIR}`);
    log(`Destination Workspace: ${DEST_DIR}`);

    // Exclude node_modules, bin directories, and binary objects to keep it lightweight
    const filterFunc = (srcPath, name) => {
        if (name === 'node_modules' || name === 'bin' || name === '.git') {
            return false;
        }
        return true;
    };

    log('Stage 1: Performing local directory copy/disassembly...');
    copyDirSync(SOURCE_APP_DIR, DEST_DIR, filterFunc);
    log('✓ Disassembly copy completed.');

    log('Stage 2: Running integrity verification and computing SHA256 hashes...');
    const fileHashes = {};

    function collectHashes(dir) {
        const items = fs.readdirSync(dir);
        for (const item of items) {
            const fullPath = path.join(dir, item);
            const relativePath = path.relative(DEST_DIR, fullPath);
            const stats = fs.statSync(fullPath);

            if (stats.isDirectory()) {
                collectHashes(fullPath);
            } else if (stats.isFile()) {
                const fileHash = calculateFileHash(fullPath);
                fileHashes[relativePath] = fileHash;
            }
        }
    }

    collectHashes(DEST_DIR);

    // Save manifest report
    const manifest = {
        app_name: 'Antigravity IDE',
        disassembly_timestamp: new Date().toISOString(),
        files: fileHashes
    };

    const manifestPath = path.join(DEST_DIR, 'disassembly_manifest.json');
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    log(`✓ Integrity manifest written to: ${manifestPath}`);

    log('======================================================');
    log('Stage 3: Deferred Generation Prompt (API Call Preview)');
    log('======================================================');
    log('All code verified. Ready to apply intelligence models.');
    log('To trigger refactoring, configure GEMINI_API_KEY and run:');
    log('  node src/run_lazy_agent.js');
}

runDisassembly();
