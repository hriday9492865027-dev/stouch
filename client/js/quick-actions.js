/**
 * Digital Touchpad Quick Actions & Power Safety Dock (PRD v2.0 Section 09)
 * Handles allowlisted Windows shortcuts, media controls, and multi-step
 * destructive power action safety dialogs with 10s countdown.
 */

class QuickActionsManager {
  constructor(protocol) {
    this.protocol = protocol;
    this.countdownTimer = null;
    this.countdownRemaining = 10;
    this.pendingPowerAction = null;
    this.init();
  }

  init() {
    this.bindActionButtons();
    this.bindPowerDialog();
  }

  bindActionButtons() {
    document.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const action = btn.getAttribute('data-action');
        this.triggerAction(action);
      });
    });

    document.querySelectorAll('[data-power]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const powerType = btn.getAttribute('data-power');
        this.showPowerConfirmation(powerType);
      });
    });
  }

  triggerAction(actionId) {
    if (navigator.vibrate) navigator.vibrate(20);
    this.protocol.sendAction(actionId);
  }

  showPowerConfirmation(powerType) {
    this.pendingPowerAction = powerType;
    this.countdownRemaining = 10;

    const modal = document.getElementById('powerModal');
    const title = document.getElementById('powerModalTitle');
    const desc = document.getElementById('powerModalDesc');
    const countdownEl = document.getElementById('powerCountdown');
    const confirmBtn = document.getElementById('powerConfirmBtn');

    if (!modal) return;

    const labels = {
      'shutdown': 'Shut Down PC',
      'restart': 'Restart PC',
      'sleep': 'Put PC to Sleep'
    };

    title.textContent = labels[powerType] || 'System Power Action';
    desc.textContent = `Are you sure? Windows will execute ${powerType} in 10 seconds. You can cancel at any time.`;
    confirmBtn.textContent = `Execute ${powerType.toUpperCase()} Now`;
    countdownEl.textContent = this.countdownRemaining;
    modal.classList.remove('hidden');

    if (this.countdownTimer) clearInterval(this.countdownTimer);
    this.countdownTimer = setInterval(() => {
      this.countdownRemaining--;
      countdownEl.textContent = this.countdownRemaining;
      if (this.countdownRemaining <= 0) {
        clearInterval(this.countdownTimer);
        this.executePendingPower();
      }
    }, 1000);
  }

  cancelPowerAction() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
    this.pendingPowerAction = null;
    const modal = document.getElementById('powerModal');
    if (modal) modal.classList.add('hidden');
    if (navigator.vibrate) navigator.vibrate(10);
  }

  executePendingPower() {
    if (!this.pendingPowerAction) return;
    const action = this.pendingPowerAction;
    this.cancelPowerAction(); // hides modal
    this.protocol.sendAction('system_power', { type: action });
  }

  bindPowerDialog() {
    const cancelBtn = document.getElementById('powerCancelBtn');
    const confirmBtn = document.getElementById('powerConfirmBtn');

    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => this.cancelPowerAction());
    }
    if (confirmBtn) {
      confirmBtn.addEventListener('click', () => this.executePendingPower());
    }
  }
}

window.QuickActionsManager = QuickActionsManager;

