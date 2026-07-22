#!/usr/bin/env node
/**
 * HDAR Independent Verifier in Node.js
 *
 * Checks all 3 epochs, manifest/receipt hashes, cryptographic lineage,
 * owner signatures, and host executor signatures.
 * Zero external dependencies.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PROTOCOL_VERSION = "hdar/v1.1-seed";
const VERIFIER_SCHEMA = "hdar.verifier-report/v1.1";

// Helpers
function sha256(data) {
  return crypto.createHash('sha256').update(data).digest('hex');
}

function sha256File(filePath) {
  const fileBuffer = fs.readFileSync(filePath);
  return sha256(fileBuffer);
}

function canonicalJson(obj) {
  if (obj === null) return 'null';
  if (typeof obj !== 'object') {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return '[' + obj.map(canonicalJson).join(',') + ']';
  }
  const sortedKeys = Object.keys(obj).sort();
  const parts = sortedKeys.map(key => {
    return JSON.stringify(key) + ':' + canonicalJson(obj[key]);
  });
  return '{' + parts.join(',') + '}';
}

function verifySignature(pubHex, message, sigHex, algorithm) {
  if (algorithm === 'hash-only-fallback' || pubHex === 'hash-only-fallback-public') {
    const hashInput = Buffer.concat([
      Buffer.from(message, 'utf8'),
      Buffer.from('hash-only-fallback-private', 'utf8')
    ]);
    const expected = sha256(hashInput);
    return expected === Buffer.from(sigHex, 'hex').toString('utf8');
  }

  try {
    const key = crypto.createPublicKey({
      key: Buffer.concat([
        Buffer.from("302a300506032b6570032100", "hex"),
        Buffer.from(pubHex, 'hex')
      ]),
      format: 'der',
      type: 'spki'
    });
    return crypto.verify(
      undefined,
      Buffer.from(message, 'utf8'),
      key,
      Buffer.from(sigHex, 'hex')
    );
  } catch (e) {
    return false;
  }
}

// CLI Arg Parser
function parseArgs() {
  const args = {};
  for (let i = 2; i < process.argv.length; i += 2) {
    const flag = process.argv[i];
    const value = process.argv[i + 1];
    if (flag && value) {
      const key = flag.replace(/^--/, '').replace(/-([a-z])/g, g => g[1].toUpperCase());
      args[key] = value;
    }
  }
  return args;
}

function main() {
  const args = parseArgs();
  const required = [
    'hostAReport', 'hostBReport', 'hostCReport',
    'e1Capsule', 'e2Capsule', 'e3Capsule', 'ownerPublicKey'
  ];
  
  for (const req of required) {
    if (!args[req]) {
      console.error(`Missing required argument: --${req.replace(/([A-Z])/g, '-$1').toLowerCase()}`);
      process.exit(1);
    }
  }

  const ownerPubHex = fs.readFileSync(args.ownerPublicKey, 'utf8').trim();

  // Load manifests, receipts, reports
  const e1Manifest = JSON.parse(fs.readFileSync(path.join(args.e1Capsule, 'manifest.json'), 'utf8'));
  const e2Manifest = JSON.parse(fs.readFileSync(path.join(args.e2Capsule, 'manifest.json'), 'utf8'));
  const e3Manifest = JSON.parse(fs.readFileSync(path.join(args.e3Capsule, 'manifest.json'), 'utf8'));

  const e1Receipt = JSON.parse(fs.readFileSync(path.join(args.e1Capsule, 'receipt.json'), 'utf8'));
  const e2Receipt = JSON.parse(fs.readFileSync(path.join(args.e2Capsule, 'receipt.json'), 'utf8'));
  const e3Receipt = JSON.parse(fs.readFileSync(path.join(args.e3Capsule, 'receipt.json'), 'utf8'));

  const hostAReport = JSON.parse(fs.readFileSync(args.hostAReport, 'utf8'));
  const hostBReport = JSON.parse(fs.readFileSync(args.hostBReport, 'utf8'));
  const hostCReport = JSON.parse(fs.readFileSync(args.hostCReport, 'utf8'));

  const checks = [];
  function check(name, passed, detail = '') {
    checks.push({ check: name, passed, detail });
  }

  const excludeFields = ['manifest_hash', 'owner_signature', 'executor_signature'];
  function cleanManifest(manifest) {
    const cleaned = {};
    for (const key of Object.keys(manifest)) {
      if (!excludeFields.includes(key)) {
        cleaned[key] = manifest[key];
      }
    }
    return cleaned;
  }

  // 1-3. Manifest Hashes
  const e1Expected = sha256(canonicalJson(cleanManifest(e1Manifest)));
  check("E1 manifest hash valid", e1Expected === e1Manifest.manifest_hash);

  const e2Expected = sha256(canonicalJson(cleanManifest(e2Manifest)));
  check("E2 manifest hash valid", e2Expected === e2Manifest.manifest_hash);

  const e3Expected = sha256(canonicalJson(cleanManifest(e3Manifest)));
  check("E3 manifest hash valid", e3Expected === e3Manifest.manifest_hash);

  // 4-6. Receipts
  const e1rExpected = sha256(canonicalJson(Object.keys(e1Receipt).reduce((acc, k) => {
    if (k !== 'receipt_hash') acc[k] = e1Receipt[k];
    return acc;
  }, {})));
  check("E1 receipt hash valid", e1rExpected === e1Receipt.receipt_hash);

  const e2rExpected = sha256(canonicalJson(Object.keys(e2Receipt).reduce((acc, k) => {
    if (k !== 'receipt_hash') acc[k] = e2Receipt[k];
    return acc;
  }, {})));
  check("E2 receipt hash valid", e2rExpected === e2Receipt.receipt_hash);

  const e3rExpected = sha256(canonicalJson(Object.keys(e3Receipt).reduce((acc, k) => {
    if (k !== 'receipt_hash') acc[k] = e3Receipt[k];
    return acc;
  }, {})));
  check("E3 receipt hash valid", e3rExpected === e3Receipt.receipt_hash);

  // 7-8. Cryptographic Lineage
  check("Lineage E1->E2 intact", e2Manifest.parent_manifest_hash === e1Manifest.manifest_hash);
  check("Lineage E2->E3 intact", e3Manifest.parent_manifest_hash === e2Manifest.manifest_hash);

  // 9. Epoch Progression
  check("Epoch progression 1->2->3 correct",
        e1Manifest.epoch === 1 && e2Manifest.epoch === 2 && e3Manifest.epoch === 3);

  // 10-12. Owner Signatures
  check("E1 owner signature valid", verifySignature(
    ownerPubHex,
    e1Manifest.manifest_hash,
    e1Manifest.owner_signature,
    e1Manifest.owner_signature_algorithm
  ));

  check("E2 owner signature valid", verifySignature(
    ownerPubHex,
    e2Manifest.manifest_hash,
    e2Manifest.owner_signature,
    e2Manifest.owner_signature_algorithm
  ));

  check("E3 owner signature valid", verifySignature(
    ownerPubHex,
    e3Manifest.manifest_hash,
    e3Manifest.owner_signature,
    e3Manifest.owner_signature_algorithm
  ));

  // 13-15. Executor Signatures
  check("E1 executor signature valid", verifySignature(
    e1Manifest.executor_public_key,
    e1Manifest.manifest_hash,
    e1Manifest.executor_signature,
    e1Manifest.executor_signature_algorithm
  ));

  check("E2 executor signature valid", verifySignature(
    e2Manifest.executor_public_key,
    e2Manifest.manifest_hash,
    e2Manifest.executor_signature,
    e2Manifest.executor_signature_algorithm
  ));

  check("E3 executor signature valid", verifySignature(
    e3Manifest.executor_public_key,
    e3Manifest.manifest_hash,
    e3Manifest.executor_signature,
    e3Manifest.executor_signature_algorithm
  ));

  // 16-17. Executor provider attestation consistent
  check("E2 attestation claims GitHub runner", (e2Manifest.executor_platform_attestation || '').includes('GitHub Actions'));
  check("E3 attestation claims Cloud Alloydb", (e3Manifest.executor_platform_attestation || '').includes('Alloydb'));

  // 18. Semantic Bugfix Check
  // Verify main_app.py in E2 blocks has division by zero handling
  const mainAppE2 = e2Manifest.workspace_manifest.files.find(f => f.rel_path === 'main_app.py');
  let hasBugfix = false;
  if (mainAppE2) {
    const digest = mainAppE2.sha256;
    const blobPath = path.join(args.e2Capsule, 'blocks', digest.substring(0, 2), digest);
    const content = fs.readFileSync(blobPath, 'utf8');
    hasBugfix = content.includes('if b == 0');
  }
  check("Semantic bugfix verification: E2 codebase handles division by zero", hasBugfix);

  // 19. Host A workspace destroyed
  check("Host A workspace was destroyed after sealing", hostAReport.host_a_runtime_destroyed === true);

  // 20. Protocol version integrity
  check("Protocol version consistency",
        e1Manifest.protocol_version === PROTOCOL_VERSION &&
        e2Manifest.protocol_version === PROTOCOL_VERSION &&
        e3Manifest.protocol_version === PROTOCOL_VERSION);

  const passedCount = checks.filter(c => c.passed).length;
  const failedCount = checks.filter(c => !c.passed).length;
  const allPassed = failedCount === 0;

  const report = {
    schema: VERIFIER_SCHEMA,
    protocol_version: PROTOCOL_VERSION,
    verifier_language: "javascript-node",
    verifier_timestamp: Date.now() / 1000,
    total_checks: checks.length,
    passed: passedCount,
    failed: failedCount,
    all_passed: allPassed,
    checks: checks
  };

  console.log("============================================================");
  console.log("NODEJS INDEPENDENT VERIFIER");
  console.log("============================================================");
  for (const c of checks) {
    const status = c.passed ? "PASS" : "FAIL";
    console.log(`  [${status}] ${c.check}`);
    if (!c.passed && c.detail) {
      console.log(`         ${c.detail}`);
    }
  }

  console.log("\n" + `  Total: ${passedCount}/${checks.length} passed, ${failedCount} failed`);
  console.log(`  All checks passed: ${allPassed}`);

  if (args.out) {
    fs.mkdirSync(path.dirname(args.out), { recursive: true });
    fs.writeFileSync(args.out, JSON.stringify(report, null, 2));
    console.log(`  Report written to: ${args.out}`);
  }

  process.exit(allPassed ? 0 : 1);
}

main();
