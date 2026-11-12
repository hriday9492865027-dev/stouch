/**
 * Digital Touchpad - Main Application Entrypoint
 * Coordinates UI, PWA lifecycle, WakeLock, and system events.
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Protocol Client
  const statusDot = document.getElementById('statusDot');
  const pcName = document.getElementById('pcName');
  const latencyBadge = document.getElementById('latencyBadge');
  const dragBadge = document.getElementById('dragBadge');
  const gestureFeed = document.getElementById('gestureFeed');

  const protocol = new TouchpadProtocol({
    onStateChange: (state, payload) => {
      statusDot.className = 'status-dot';
      if (state === 'connected' || state === 'ready') {
        statusDot.classList.add('connected');
        pcName.textContent = (payload && payload.host_name) ? payload.host_name : 'Windows PC (Connected)';
      } else if (state === 'need_pc_ip') {
        const pcIpModal = document.getElementById('pcIpModal');
        const pcIpInput = document.getElementById('pcIpInput');
        if (pcIpModal) {
          pcIpModal.classList.remove('hidden');
          const saved = localStorage.getItem('stouch_pc_ip');
          if (saved && pcIpInput) pcIpInput.value = saved;
        }
        pcName.textContent = 'Enter PC IP...';
      } else if (state === 'pairing_required') {
        statusDot.classList.add('pairing');
        pcName.textContent = 'Pairing Required...';
      } else if (state === 'connecting') {
        statusDot.classList.add('pairing');
        pcName.textContent = 'Connecting...';
      } else {
        pcName.textContent = 'Disconnected';
      }
    },
    onLatencyUpdate: (ms) => {
      latencyBadge.textContent = `${ms} ms`;
    },
    onActionResult: (res) => {
      showGestureFeedback(res.action + ': ' + (res.status || 'OK'));
    },
    onError: (err) => {
      console.warn('Protocol error:', err);
    }
  });

  // Automatically initiate connection to host
  protocol.connect();

  // 2. Initialize Gesture Engine
  const surfaceEl = document.getElementById('touchpadSurface');
  const gestures = new GestureEngine(surfaceEl, protocol, {
    onGestureDetected: (name) => {
      showGestureFeedback(name);
    },
    onDragStateChanged: (isActive) => {
      if (isActive) {
        dragBadge.classList.add('active');
      } else {
        dragBadge.classList.remove('active');
      }
    }
  });

  let feedbackTimeout = null;
  function showGestureFeedback(text) {
    if (!gestureFeed) return;
    gestureFeed.textContent = text;
    gestureFeed.classList.add('show');
    if (feedbackTimeout) clearTimeout(feedbackTimeout);
    feedbackTimeout = setTimeout(() => {
      gestureFeed.classList.remove('show');
    }, 1200);
  }

  // 3. Initialize Quick Actions
  const quickActions = new QuickActionsManager(protocol);

  // 4. Physical Click Buttons
  const leftClickBtn = document.getElementById('leftClickBtn');
  const rightClickBtn = document.getElementById('rightClickBtn');

  if (leftClickBtn) {
    leftClickBtn.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      gestures.vibrate(15);
      protocol.sendButtonState('left', 'down');
    });
    leftClickBtn.addEventListener('pointerup', (e) => {
      e.preventDefault();
      protocol.sendButtonState('left', 'up');
    });
  }

  if (rightClickBtn) {
    rightClickBtn.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      gestures.vibrate(20);
      protocol.sendButtonState('right', 'down');
    });
    rightClickBtn.addEventListener('pointerup', (e) => {
      e.preventDefault();
      protocol.sendButtonState('right', 'up');
    });
  }

  // 5. Dock Tabs Switching
  const tabs = document.querySelectorAll('.dock-tab');
  const sheets = {
    'apps': document.getElementById('sheet-apps'),
    'media': document.getElementById('sheet-media'),
    'presenter': document.getElementById('sheet-presenter'),
    'power': document.getElementById('sheet-power')
  };

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      Object.values(sheets).forEach(s => s.classList.remove('active'));

      tab.classList.add('active');
      const target = tab.getAttribute('data-tab');
      if (sheets[target]) sheets[target].classList.add('active');
      if (navigator.vibrate) navigator.vibrate(10);
    });
  });

  // 6. Coach Pill Dismiss
  const coachPill = document.getElementById('coachPill');
  const closeCoachBtn = document.getElementById('closeCoachBtn');
  if (closeCoachBtn && coachPill) {
    closeCoachBtn.addEventListener('click', () => {
      coachPill.style.display = 'none';
    });
  }

  // 7. Bluetooth & Devices Modal
  const btBtn = document.getElementById('btBtn');
  const btModal = document.getElementById('bluetoothModal');
  const closeBtModalBtn = document.getElementById('closeBtModalBtn');
  const webBtScanBtn = document.getElementById('webBtScanBtn');
  const btStatusMsg = document.getElementById('btStatusMsg');

  if (btBtn && btModal) {
    btBtn.addEventListener('click', () => {
      btModal.classList.remove('hidden');
      if (btStatusMsg) btStatusMsg.textContent = '';
    });
    closeBtModalBtn.addEventListener('click', () => {
      btModal.classList.add('hidden');
    });

    if (webBtScanBtn) {
      webBtScanBtn.addEventListener('click', async () => {
        if (!navigator.bluetooth) {
          btStatusMsg.textContent = 'Web Bluetooth is not supported on this browser (use Chrome on Android/Desktop).';
          btStatusMsg.style.color = '#ef4444';
          return;
        }

        try {
          btStatusMsg.textContent = 'Requesting Bluetooth device pairing...';
          btStatusMsg.style.color = '#38bdf8';
          const device = await navigator.bluetooth.requestDevice({
            acceptAllDevices: true
          });
          btStatusMsg.textContent = `Paired with ${device.name || 'Bluetooth Device'}.`;
          btStatusMsg.style.color = '#10b981';
        } catch (err) {
          if (err.name === 'NotFoundError') {
            btStatusMsg.textContent = 'Scan cancelled by user.';
            btStatusMsg.style.color = '#94a3b8';
          } else {
            btStatusMsg.textContent = `Bluetooth: ${err.message}`;
            btStatusMsg.style.color = '#ef4444';
          }
        }
      });
    }
  }

  // 8. Diagnostics Modal & Redacted Telemetry Export (PRD Section 15 & AT-016)
  const diagBtn = document.getElementById('diagBtn');
  const diagModal = document.getElementById('diagModal');
  const closeDiagModalBtn = document.getElementById('closeDiagModalBtn');
  const diagContent = document.getElementById('diagContent');
  const exportDiagBtn = document.getElementById('exportDiagBtn');

  if (diagBtn && diagModal) {
    diagBtn.addEventListener('click', async () => {
      diagModal.classList.remove('hidden');
      diagContent.textContent = 'Fetching diagnostic report...';
      try {
        const res = await fetch('/api/diagnostics');
        const data = await res.json();
        diagContent.textContent = JSON.stringify(data, null, 2);
      } catch (e) {
        diagContent.textContent = `Diagnostic error: ${e.message}\nMake sure the companion receiver is running.`;
      }
    });

    if (closeDiagModalBtn) {
      closeDiagModalBtn.addEventListener('click', () => diagModal.classList.add('hidden'));
    }

    if (exportDiagBtn) {
      exportDiagBtn.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/diagnostics/export');
          const data = await res.json();
          const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `stouch_diagnostics_${Date.now()}.json`;
          a.click();
          URL.revokeObjectURL(url);
          showGestureFeedback('Diagnostics Exported');
        } catch (e) {
          alert('Failed to export diagnostics: ' + e.message);
        }
      });
    }
  }

  // 9. Fullscreen Toggle
  const fullscreenBtn = document.getElementById('fullscreenBtn');
  if (fullscreenBtn) {
    fullscreenBtn.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });
  }

  // 8. Settings Modal & Sliders
  const settingsBtn = document.getElementById('settingsBtn');
  const settingsModal = document.getElementById('settingsModal');
  const closeSettingsBtn = document.getElementById('closeSettingsBtn');
  const sensSlider = document.getElementById('sensSlider');
  const sensVal = document.getElementById('sensVal');
  const scrollSlider = document.getElementById('scrollSlider');
  const scrollVal = document.getElementById('scrollVal');
  const naturalScrollToggle = document.getElementById('naturalScrollToggle');
  const hapticsToggle = document.getElementById('hapticsToggle');

  if (settingsBtn && settingsModal) {
    settingsBtn.addEventListener('click', () => settingsModal.classList.remove('hidden'));
    closeSettingsBtn.addEventListener('click', () => settingsModal.classList.add('hidden'));

    sensSlider.addEventListener('input', (e) => {
      const v = parseFloat(e.target.value);
      sensVal.textContent = `${v.toFixed(1)}x`;
      gestures.sensitivity = v;
    });

    scrollSlider.addEventListener('input', (e) => {
      const v = parseFloat(e.target.value);
      scrollVal.textContent = `${v.toFixed(1)}x`;
      gestures.scrollSpeed = v;
    });

    naturalScrollToggle.addEventListener('change', (e) => {
      gestures.naturalScroll = e.target.checked;
    });

    hapticsToggle.addEventListener('change', (e) => {
      gestures.hapticsEnabled = e.target.checked;
    });
  }

  // 10. Manual PC IP Connection (Vercel Hosting)
  const pcIpModal = document.getElementById('pcIpModal');
  const pcIpInput = document.getElementById('pcIpInput');
  const savePcIpBtn = document.getElementById('savePcIpBtn');

  if (savePcIpBtn) {
    savePcIpBtn.addEventListener('click', () => {
      const val = (pcIpInput.value || '').trim();
      if (val) {
        localStorage.setItem('stouch_pc_ip', val);
        if (pcIpModal) pcIpModal.classList.add('hidden');
        protocol.connect();
      }
    });
  }

  // 11. Screen Wake Lock (Prevent phone screen dimming while using touchpad)
  async function requestWakeLock() {
    if ('wakeLock' in navigator) {
      try {
        await navigator.wakeLock.request('screen');
        console.log('[WakeLock] Active');
      } catch (err) {
        console.log('[WakeLock] Error:', err);
      }
    }
  }
  requestWakeLock();
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') requestWakeLock();
  });

  // 10. Register Service Worker for PWA
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js')
      .then(reg => console.log('[PWA] Service Worker registered'))
      .catch(err => console.log('[PWA] Service Worker registration failed', err));
  }
});

