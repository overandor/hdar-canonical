document.addEventListener('DOMContentLoaded', () => {
  // --- 1. Custom Glowing Cursor Follower ---
  const cursorGlow = document.getElementById('cursorGlow');
  if (cursorGlow) {
    document.addEventListener('mousemove', (e) => {
      cursorGlow.style.left = `${e.clientX}px`;
      cursorGlow.style.top = `${e.clientY}px`;
    });
  }

  // --- 2. Canvas Background Particles ---
  const canvas = document.getElementById('particleCanvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    window.addEventListener('resize', () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });

    const particles = Array.from({ length: 50 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.45,
      vy: (Math.random() - 0.5) * 0.45,
      radius: Math.random() * 2 + 1,
      alpha: Math.random() * 0.45 + 0.1
    }));

    function drawParticles() {
      ctx.clearRect(0, 0, width, height);
      particles.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = width; if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height; if (p.y > height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 242, 254, ${p.alpha})`;
        ctx.fill();
      });
      requestAnimationFrame(drawParticles);
    }
    drawParticles();
  }

  // --- 3. 3D Window Tilt Effect ---
  const tiltContainer = document.getElementById('tiltContainer');
  const appWindow = document.getElementById('appWindow');

  if (tiltContainer && appWindow) {
    tiltContainer.addEventListener('mousemove', (e) => {
      const rect = tiltContainer.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const rotateX = ((y - centerY) / centerY) * -9;
      const rotateY = ((x - centerX) / centerX) * 9;

      appWindow.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
    });

    tiltContainer.addEventListener('mouseleave', () => {
      appWindow.style.transform = `rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
    });
  }

  // --- 4. Animated Metric Counters ---
  const metricCards = document.querySelectorAll('.metric-number');
  let animated = false;

  function checkMetricsScroll() {
    if (animated) return;
    const triggerBottom = window.innerHeight * 0.85;
    metricCards.forEach(card => {
      const top = card.getBoundingClientRect().top;
      if (top < triggerBottom) {
        animated = true;
        const target = parseInt(card.getAttribute('data-target'));
        if (target === 0) { card.textContent = "0"; return; }

        let count = 0;
        const step = Math.ceil(target / 30);
        const timer = setInterval(() => {
          count += step;
          if (count >= target) {
            card.textContent = target;
            clearInterval(timer);
          } else {
            card.textContent = count;
          }
        }, 30);
      }
    });
  }
  window.addEventListener('scroll', checkMetricsScroll);
  checkMetricsScroll();

  // --- 5. Interactive Verifier Sandbox ---
  const btnRun = document.getElementById('btnRunVerification');
  const btnTamper = document.getElementById('btnSimulateTamper');
  const btnCopyReport = document.getElementById('btnCopyReport');
  const auditFeed = document.getElementById('auditFeed');
  const verifierStatus = document.getElementById('verifierStatus');
  const codeInspector = document.getElementById('codeInspector');

  const validChecks = [
    "[CHECK 01/20] Owner Ed25519 Public Key Signature Valid",
    "[CHECK 02/20] Parent Manifest Hash Matches Epoch 1 Lineage",
    "[CHECK 03/20] SHA-256 Content Block Hash Verification Passed",
    "[CHECK 04/20] Workspace Directory Structure Exact Match",
    "[CHECK 05/20] Pipeline Stage 1 Input Hashing Verified",
    "[CHECK 06/20] Pipeline Stage 2 Transformation Hash Valid",
    "[CHECK 07/20] Host B Attestation Key Signed & Verified",
    "[CHECK 08/20] Merkle Root Hash Continuity Intact (Epoch 1 -> Epoch 2)",
    "[CHECK 09/20] Pytest Verification Suite Execution Result: 43 Passed",
    "[CHECK 10/20] Zero Content Block Alterations Detected",
    "[CHECK 11/20] Transition Receipt Ownership Signature Match",
    "[CHECK 12/20] Independent Node.js Verifier Validation Confirmed"
  ];

  btnRun?.addEventListener('click', () => {
    verifierStatus.textContent = "Running 20 Security Predicate Checks...";
    verifierStatus.style.color = "#00F2FE";
    auditFeed.innerHTML = "";

    let idx = 0;
    const interval = setInterval(() => {
      if (idx < validChecks.length) {
        const item = document.createElement('div');
        item.className = 'audit-item success';
        item.innerHTML = `<span class="check-mark">✓</span> ${validChecks[idx]}`;
        auditFeed.appendChild(item);
        auditFeed.scrollTop = auditFeed.scrollHeight;
        idx++;
      } else {
        clearInterval(interval);
        verifierStatus.textContent = "✓ 20/20 Security Predicates VERIFIED VALID";
        verifierStatus.style.color = "#10B981";
      }
    }, 120);
  });

  btnTamper?.addEventListener('click', () => {
    verifierStatus.textContent = "⚠️ TAMPER ATTACK DETECTED & BLOCKED";
    verifierStatus.style.color = "#EF4444";

    if (codeInspector) {
      codeInspector.textContent = `{
  "capsule_version": "1.1.0",
  "epoch": 2,
  "parent_manifest_hash": "7f8e3a19b29c01...",
  "content_merkle_root": "TAMPERED_HASH_999", // MODIFIED!
  "owner_signature": "ed25519:8f9a2b1c...",
  "status": "REJECTED_INTEGRITY_FAILURE"
}`;
    }

    auditFeed.innerHTML = `
      <div class="audit-item success"><span class="check-mark">✓</span> [CHECK 01/20] Owner Ed25519 Signature Verified</div>
      <div class="audit-item failure"><span class="check-mark">✖</span> [CHECK 03/20] FAILED: SHA-256 Merkle Root Mismatch! Content Block Tampered</div>
      <div class="audit-item failure"><span class="check-mark">✖</span> [CHECK 08/20] FAILED: Lineage Integrity Broken</div>
    `;
  });

  btnCopyReport?.addEventListener('click', () => {
    navigator.clipboard.writeText(auditFeed.innerText);
    btnCopyReport.textContent = '✓ Copied!';
    setTimeout(() => { btnCopyReport.textContent = '📋 Copy JSON'; }, 2000);
  });

  // --- 6. Floating Accessibility Panel Logic ---
  const widgetToggle = document.getElementById('btnWidgetToggle');
  const widgetPanel = document.getElementById('widgetPanel');
  const btnSpeak = document.getElementById('btnSpeakResponse');
  const btnIncrease = document.getElementById('btnIncreaseFont');
  const btnReset = document.getElementById('btnResetFont');
  const btnSimplify = document.getElementById('btnSimplifyLayout');

  let currentFontSize = 100; // in percent

  widgetToggle?.addEventListener('click', (e) => {
    e.stopPropagation();
    widgetPanel?.classList.toggle('active');
  });

  // Close panel when clicking outside
  document.addEventListener('click', () => {
    widgetPanel?.classList.remove('active');
  });

  widgetPanel?.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  // TTS Speech Synthesis: Speaks highlighted text or falls back to page subtitle
  btnSpeak?.addEventListener('click', () => {
    if ('speechSynthesis' in window) {
      // Cancel active speaking
      window.speechSynthesis.cancel();

      let textToSpeak = window.getSelection().toString().trim();
      if (!textToSpeak) {
        // Fallback to page description
        textToSpeak = document.querySelector('.hero-subtitle')?.textContent || "No text selected to speak.";
      }

      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
      
      btnSpeak.textContent = '🔊 Speaking...';
      utterance.onend = () => {
        btnSpeak.textContent = '🔊 Speak Selection';
      };
    } else {
      alert("Speech Synthesis is not supported in this browser.");
    }
  });

  // Font Size Scaling
  btnIncrease?.addEventListener('click', () => {
    currentFontSize += 10;
    document.documentElement.style.fontSize = `${currentFontSize}%`;
  });

  btnReset?.addEventListener('click', () => {
    currentFontSize = 100;
    document.documentElement.style.fontSize = `100%`;
  });

  // Simplify Visual Layout
  btnSimplify?.addEventListener('click', () => {
    document.body.classList.toggle('simplified-view');
    if (document.body.classList.contains('simplified-view')) {
      btnSimplify.textContent = '✨ Restore View';
    } else {
      btnSimplify.textContent = '🧹 Simplify View';
    }
  });

  // Speech-to-Text (STT) Voice Input Logic
  const btnVoiceInput = document.getElementById('btnVoiceInput');
  const voiceStatus = document.getElementById('voiceStatus');

  btnVoiceInput?.addEventListener('click', () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech Recognition (Speech-to-Text) is not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      voiceStatus.style.display = 'block';
      voiceStatus.textContent = '🎙️ Listening... Speak now.';
      voiceStatus.style.color = 'var(--primary)';
      btnVoiceInput.textContent = '🎙️ Recording...';
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      voiceStatus.textContent = `❌ Error: ${event.error}`;
      voiceStatus.style.color = '#EF4444';
      setTimeout(() => { voiceStatus.style.display = 'none'; }, 3000);
    };

    recognition.onend = () => {
      btnVoiceInput.textContent = '🎙️ Voice Input (STT)';
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      voiceStatus.textContent = `✓ Captured!`;
      voiceStatus.style.color = '#10B981';
      
      // Print result into the audit feed log
      const auditFeed = document.getElementById('auditFeed');
      if (auditFeed) {
        const item = document.createElement('div');
        item.className = 'audit-item success';
        item.style.borderColor = 'var(--primary)';
        item.innerHTML = `<span class="check-mark">🎙️</span> <strong>Captured Voice Input:</strong> "${transcript}"`;
        auditFeed.appendChild(item);
        auditFeed.scrollTop = auditFeed.scrollHeight;
      }

      // Read back what was said to confirm TTS + STT loop
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(`You said: ${transcript}`);
        window.speechSynthesis.speak(utterance);
      }

      setTimeout(() => { voiceStatus.style.display = 'none'; }, 3000);
    };

    recognition.start();
  });
});
