/**
 * Digital Touchpad Gesture Engine (PRD v2.0 Section 07 & 08)
 * Implements multi-touch state machine, deadzone jitter suppression,
 * tap-hold drag, two-finger scrolling, pinch zoom, and three-finger shortcuts.
 */

class GestureEngine {
  constructor(surfaceElement, protocol, options = {}) {
    this.surface = surfaceElement;
    this.protocol = protocol;

    // Configurable thresholds from PRD
    this.tapDurationMax = options.tapDurationMax || 180; // ms
    this.tapMovementMax = options.tapMovementMax || 12;  // px / dp
    this.doubleTapIntervalMax = options.doubleTapIntervalMax || 300; // ms
    this.holdToDragMin = options.holdToDragMin || 350;   // ms
    this.multiTouchSettle = options.multiTouchSettle || 80; // ms
    this.swipeDistanceMin = options.swipeDistanceMin || 70; // px
    this.sensitivity = options.sensitivity || 1.4;
    this.scrollSpeed = options.scrollSpeed || 1.0;
    this.naturalScroll = options.naturalScroll !== undefined ? options.naturalScroll : true;
    this.hapticsEnabled = options.hapticsEnabled !== undefined ? options.hapticsEnabled : true;

    // Active touch tracking
    this.touches = new Map(); // identifier -> { startX, startY, currentX, currentY, startTime }
    this.lastTapTime = 0;
    this.lastTapX = 0;
    this.lastTapY = 0;
    this.holdTimer = null;
    this.isDragging = false;
    this.hasMovedPastDeadzone = false;
    this.gestureLocked = null; // 'drag', 'scroll', 'pinch', '3swipe'
    this.initialPinchDistance = 0;

    // Callbacks for UI state
    this.onGestureDetected = options.onGestureDetected || (() => {});
    this.onDragStateChanged = options.onDragStateChanged || (() => {});

    this.bindEvents();
  }

  vibrate(ms = 15) {
    if (this.hapticsEnabled && navigator.vibrate) {
      try { navigator.vibrate(ms); } catch (e) {}
    }
  }

  bindEvents() {
    const el = this.surface;

    // Touch events provide multi-touch details reliably on mobile browsers
    el.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
    el.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
    el.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: false });
    el.addEventListener('touchcancel', (e) => this.handleTouchCancel(e), { passive: false });

    // Window blur / visibility change safety release
    window.addEventListener('blur', () => this.emergencyRelease());
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) this.emergencyRelease();
    });
  }

  handleTouchStart(e) {
    e.preventDefault();
    const now = performance.now();

    for (let i = 0; i < e.changedTouches.length; i++) {
      const t = e.changedTouches[i];
      this.touches.set(t.identifier, {
        startX: t.clientX,
        startY: t.clientY,
        lastX: t.clientX,
        lastY: t.clientY,
        currentX: t.clientX,
        currentY: t.clientY,
        startTime: now
      });
    }

    const touchCount = this.touches.size;

    if (touchCount === 1) {
      this.hasMovedPastDeadzone = false;
      this.gestureLocked = null;

      // Start hold-to-drag timer
      const touchId = e.changedTouches[0].identifier;
      if (this.holdTimer) clearTimeout(this.holdTimer);
      this.holdTimer = setTimeout(() => {
        if (this.touches.size === 1 && !this.hasMovedPastDeadzone) {
          // Engaged tap-hold drag!
          this.isDragging = true;
          this.gestureLocked = 'drag';
          this.vibrate(25);
          this.protocol.sendButtonState('left', 'down');
          this.onDragStateChanged(true);
          this.onGestureDetected('Tap-hold Dragging');
        }
      }, this.holdToDragMin);

    } else if (touchCount === 2) {
      // 2 fingers landed
      if (this.holdTimer) clearTimeout(this.holdTimer);
      if (this.isDragging) {
        this.protocol.sendButtonState('left', 'up');
        this.isDragging = false;
        this.onDragStateChanged(false);
      }
      this.gestureLocked = 'scroll';
      const touchList = Array.from(this.touches.values());
      this.initialPinchDistance = Math.hypot(
        touchList[0].currentX - touchList[1].currentX,
        touchList[0].currentY - touchList[1].currentY
      );

    } else if (touchCount === 3) {
      if (this.holdTimer) clearTimeout(this.holdTimer);
      this.gestureLocked = '3swipe';
    }
  }

  handleTouchMove(e) {
    e.preventDefault();
    const touchCount = this.touches.size;

    // Use coalesced events if available for ultra-smooth 120Hz tracking
    const events = (e.getCoalescedEvents && e.getCoalescedEvents().length > 0)
      ? e.getCoalescedEvents()
      : [e];

    for (const evt of events) {
      for (let i = 0; i < evt.changedTouches.length; i++) {
        const t = evt.changedTouches[i];
        const state = this.touches.get(t.identifier);
        if (state) {
          state.currentX = t.clientX;
          state.currentY = t.clientY;
        }
      }
    }

    if (touchCount === 1) {
      const touch = Array.from(this.touches.values())[0];
      if (!touch) return;

      const totalDist = Math.hypot(touch.currentX - touch.startX, touch.currentY - touch.startY);
      if (totalDist > this.tapMovementMax) {
        this.hasMovedPastDeadzone = true;
        if (!this.isDragging && this.holdTimer) {
          clearTimeout(this.holdTimer); // cancelled hold
        }
      }

      const dx = (touch.currentX - touch.lastX) * this.sensitivity;
      const dy = (touch.currentY - touch.lastY) * this.sensitivity;

      touch.lastX = touch.currentX;
      touch.lastY = touch.currentY;

      if (dx !== 0 || dy !== 0) {
        // Pointer acceleration ballistics
        const speed = Math.hypot(dx, dy);
        const accel = speed > 15 ? 1.35 : (speed > 8 ? 1.15 : 1.0);
        this.protocol.sendPointerMove(dx * accel, dy * accel);
      }

    } else if (touchCount === 2) {
      const touchList = Array.from(this.touches.values());
      if (touchList.length < 2) return;

      const currentDist = Math.hypot(
        touchList[0].currentX - touchList[1].currentX,
        touchList[0].currentY - touchList[1].currentY
      );

      // Check if this is a pinch or scroll
      const pinchDelta = currentDist - this.initialPinchDistance;
      if (Math.abs(pinchDelta) > 40 && this.gestureLocked !== 'scroll') {
        this.gestureLocked = 'pinch';
        // Send zoom
        const zoomDelta = pinchDelta > 0 ? 1 : -1;
        this.protocol.sendEnvelope('KEY_CHORD', { keys: ['ctrl'], action: 'zoom', delta: zoomDelta });
        this.initialPinchDistance = currentDist;
        this.onGestureDetected(pinchDelta > 0 ? 'Zoom In' : 'Zoom Out');
        return;
      }

      // Scrolling
      const dy1 = touchList[0].currentY - touchList[0].lastY;
      const dy2 = touchList[1].currentY - touchList[1].lastY;
      const dx1 = touchList[0].currentX - touchList[0].lastX;
      const dx2 = touchList[1].currentX - touchList[1].lastX;

      touchList[0].lastX = touchList[0].currentX;
      touchList[0].lastY = touchList[0].currentY;
      touchList[1].lastX = touchList[1].currentX;
      touchList[1].lastY = touchList[1].currentY;

      // Average movement
      let avgDy = ((dy1 + dy2) / 2) * this.scrollSpeed;
      let avgDx = ((dx1 + dx2) / 2) * this.scrollSpeed;

      if (this.naturalScroll) {
        avgDy = -avgDy;
        avgDx = -avgDx;
      }

      if (Math.abs(avgDy) > 0.5 || Math.abs(avgDx) > 0.5) {
        // Convert to Windows wheel ticks
        this.protocol.sendScroll(avgDx * 3, avgDy * 3);
        this.onGestureDetected('Two-finger Scroll');
      }

    } else if (touchCount === 3) {
      // 3-finger swipe tracking
      const touchList = Array.from(this.touches.values());
      const avgY = (touchList[0].currentY - touchList[0].startY +
                    touchList[1].currentY - touchList[1].startY +
                    touchList[2].currentY - touchList[2].startY) / 3;
      const avgX = (touchList[0].currentX - touchList[0].startX +
                    touchList[1].currentX - touchList[1].startX +
                    touchList[2].currentX - touchList[2].startX) / 3;

      if (this.gestureLocked === '3swipe') {
        if (avgY < -this.swipeDistanceMin) {
          // Swipe up -> Task View (Win+Tab)
          this.gestureLocked = '3swipe_fired';
          this.vibrate(30);
          this.protocol.sendAction('task_view');
          this.onGestureDetected('Task View (Win+Tab)');
        } else if (avgY > this.swipeDistanceMin) {
          // Swipe down -> Show Desktop (Win+D)
          this.gestureLocked = '3swipe_fired';
          this.vibrate(30);
          this.protocol.sendAction('show_desktop');
          this.onGestureDetected('Show Desktop (Win+D)');
        } else if (Math.abs(avgX) > this.swipeDistanceMin) {
          // Swipe left/right -> Alt+Tab app switch
          this.gestureLocked = '3swipe_fired';
          this.vibrate(30);
          this.protocol.sendAction('app_switch');
          this.onGestureDetected('App Switch (Alt+Tab)');
        }
      }
    }
  }

  handleTouchEnd(e) {
    e.preventDefault();
    const now = performance.now();

    for (let i = 0; i < e.changedTouches.length; i++) {
      const t = e.changedTouches[i];
      const state = this.touches.get(t.identifier);

      if (state) {
        const duration = now - state.startTime;
        const dist = Math.hypot(t.clientX - state.startX, t.clientY - state.startY);
        const wasSingleTouch = this.touches.size === 1;

        if (this.holdTimer) {
          clearTimeout(this.holdTimer);
          this.holdTimer = null;
        }

        if (this.isDragging) {
          // End drag
          this.isDragging = false;
          this.protocol.sendButtonState('left', 'up');
          this.vibrate(15);
          this.onDragStateChanged(false);
          this.onGestureDetected('Drag Released');
        } else if (wasSingleTouch && duration <= this.tapDurationMax && dist <= this.tapMovementMax) {
          // Qualifying single tap
          const timeSinceLastTap = now - this.lastTapTime;
          const distFromLastTap = Math.hypot(t.clientX - this.lastTapX, t.clientY - this.lastTapY);

          if (timeSinceLastTap <= this.doubleTapIntervalMax && distFromLastTap <= 25) {
            // Double click
            this.protocol.sendButtonState('left', 'double_click');
            this.vibrate(25);
            this.onGestureDetected('Double Click');
            this.lastTapTime = 0; // reset
          } else {
            // Single primary click
            this.protocol.sendButtonState('left', 'click');
            this.vibrate(15);
            this.onGestureDetected('Left Click');
            this.lastTapTime = now;
            this.lastTapX = t.clientX;
            this.lastTapY = t.clientY;
          }
        } else if (this.touches.size === 2 && duration <= 220 && dist <= 20) {
          // Two-finger tap -> Right Click!
          this.protocol.sendButtonState('right', 'click');
          this.vibrate(25);
          this.onGestureDetected('Right Click');
        }
      }

      this.touches.delete(t.identifier);
    }

    if (this.touches.size === 0) {
      this.gestureLocked = null;
      this.hasMovedPastDeadzone = false;
    }
  }

  handleTouchCancel(e) {
    this.emergencyRelease();
  }

  emergencyRelease() {
    if (this.holdTimer) clearTimeout(this.holdTimer);
    this.isDragging = false;
    this.touches.clear();
    this.gestureLocked = null;
    this.onDragStateChanged(false);
    this.protocol.sendReleaseAll();
  }
}

window.GestureEngine = GestureEngine;

