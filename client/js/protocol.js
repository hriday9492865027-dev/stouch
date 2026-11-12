/**
 * Digital Touchpad Protocol Client (PRD v2.0 Section 12)
 * Handles versioned envelopes, monotonic sequence numbering,
 * heartbeat liveness, and auto-reconnection.
 */

class TouchpadProtocol {
  constructor(options = {}) {
    this.version = '2.0';
    this.sessionId = null;
    this.sequence = 0;
    this.ws = null;
    this.isConnected = false;
    this.isPaired = false;
    this.lastLatency = 0;
    this.lastHeartbeatSent = 0;
    this.heartbeatTimer = null;
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;
    this.maxReconnectBackoff = 30000;
    this.token = localStorage.getItem('stouch_token') || null;

    // Callbacks
    this.onStateChange = options.onStateChange || (() => {});
    this.onLatencyUpdate = options.onLatencyUpdate || (() => {});
    this.onActionResult = options.onActionResult || (() => {});
    this.onError = options.onError || (() => {});
  }

  connect(hostUrl) {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    if (!hostUrl) {
      const loc = window.location;
      const isCloudHosted = !['localhost', '127.0.0.1'].includes(loc.hostname) &&
                            !loc.hostname.startsWith('192.168.') &&
                            !loc.hostname.startsWith('10.') &&
                            !loc.hostname.startsWith('172.');

      // Check query parameter from QR code scan: e.g. ?pc=192.168.1.100:8000
      const urlParams = new URLSearchParams(window.location.search);
      const queryPc = urlParams.get('pc');
      if (queryPc) {
        localStorage.setItem('stouch_pc_ip', queryPc);
      }
      const savedPcIp = queryPc || localStorage.getItem('stouch_pc_ip');

      if (isCloudHosted) {
        if (savedPcIp) {
          const cleanIp = savedPcIp.replace(/^(ws:\/\/|http:\/\/)/, '').replace(/\/$/, '');
          hostUrl = `ws://${cleanIp}/ws`;
        } else {
          this.onStateChange('need_pc_ip');
          return;
        }
      } else {
        const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
        hostUrl = `${protocol}//${loc.host}/ws`;
      }
    }

    this.hostUrl = hostUrl;
    this.onStateChange('connecting');

    try {
      this.ws = new WebSocket(hostUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.sequence = 0;
        this.sendHello();
        this.startHeartbeat();
        this.onStateChange('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleMessage(msg);
        } catch (e) {
          console.error('[Protocol] Failed to parse message:', e);
        }
      };

      this.ws.onclose = () => {
        this.handleDisconnect('Socket closed');
      };

      this.ws.onerror = (err) => {
        console.warn('[Protocol] WebSocket error:', err);
        this.onError(err);
      };
    } catch (e) {
      this.handleDisconnect(e.message);
    }
  }

  handleDisconnect(reason) {
    this.isConnected = false;
    this.isPaired = false;
    this.stopHeartbeat();
    this.onStateChange('disconnected', reason);
    this.scheduleReconnect();
  }

  scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectBackoff) + Math.random() * 500;
    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => {
      console.log(`[Protocol] Attempting reconnect (${this.reconnectAttempts})...`);
      this.connect(this.hostUrl);
    }, delay);
  }

  sendEnvelope(type, payload = {}, requestId = null) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    this.sequence++;
    const envelope = {
      version: this.version,
      type: type,
      session_id: this.sessionId,
      sequence: this.sequence,
      request_id: requestId || (type.includes('REQUEST') ? 'req_' + Date.now() + '_' + Math.floor(Math.random() * 1000) : null),
      payload: payload
    };

    this.ws.send(JSON.stringify(envelope));
    return envelope.request_id;
  }

  sendHello() {
    this.sendEnvelope('SESSION_HELLO', {
      client: 'PWA Web Client',
      token: this.token
    });
  }

  sendPointerMove(dx, dy) {
    this.sendEnvelope('POINTER_MOVE', { dx: Math.round(dx), dy: Math.round(dy) });
  }

  sendButtonState(button, state) {
    // button: 'left' | 'right' | 'middle', state: 'down' | 'up' | 'click'
    this.sendEnvelope('BUTTON_STATE', { button, state });
  }

  sendScroll(dx, dy) {
    this.sendEnvelope('SCROLL', { dx: Math.round(dx), dy: Math.round(dy) });
  }

  sendKeyChord(keys) {
    // e.g. ['ctrl', 'c'] or 'Win+D'
    this.sendEnvelope('KEY_CHORD', { keys });
  }

  sendAction(actionId, params = {}) {
    return this.sendEnvelope('ACTION_REQUEST', { action: actionId, ...params });
  }

  sendReleaseAll() {
    this.sendEnvelope('RELEASE_ALL', {});
  }

  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.lastHeartbeatSent = performance.now();
        this.sendEnvelope('HEARTBEAT', { timestamp: Date.now() });
      }
    }, 2000);
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  handleMessage(msg) {
    if (!msg || !msg.type) return;

    switch (msg.type) {
      case 'SESSION_READY':
        this.sessionId = msg.session_id;
        this.isPaired = true;
        if (msg.payload && msg.payload.token) {
          this.token = msg.payload.token;
          localStorage.setItem('stouch_token', this.token);
        }
        this.onStateChange('ready', msg.payload);
        break;

      case 'PAIR_REQUEST':
        this.onStateChange('pairing_required', msg.payload);
        break;

      case 'HEARTBEAT':
        if (this.lastHeartbeatSent > 0) {
          this.lastLatency = Math.round(performance.now() - this.lastHeartbeatSent);
          this.onLatencyUpdate(this.lastLatency);
        }
        break;

      case 'ACTION_RESULT':
        this.onActionResult(msg.payload);
        break;

      case 'RELEASE_ALL':
        console.log('[Protocol] Server triggered release-all');
        break;

      default:
        console.log('[Protocol] Received message:', msg.type);
    }
  }
}

window.TouchpadProtocol = TouchpadProtocol;

