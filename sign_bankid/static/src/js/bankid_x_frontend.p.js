import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

publicWidget.registry.BankIDSignWidget = publicWidget.Widget.extend({
    selector: '#modal_bankid_ssn',
    events: {
        'click .bankid_sign_init': '_onBankIdInit',
        'click .bankid_sign_cancel': '_onBankIdCancel',
        'show.bs.modal': '_onModalShow',
    },

    init: function() {
        this._super(...arguments);
        this.orderRef = null;
        this.qrInterval = null;
        this.statusInterval = null;
        this.currentQrContent = null;
        this.res_id = null;
        this.res_model = null;
        this.ssn = null;
        this.access_token = null;
    },

    start: function() {
        const result = this._super(...arguments);

        // Configure modal to not close on outside click or escape
        this.$el.modal({
            backdrop: 'static',
            keyboard: false
        });

        // Bind modal close event
        this.$el.on('hidden.bs.modal', this._onModalClosed.bind(this));
        return result;
    },

    /**
     * Reset UI state when modal is shown
     */
    _onModalShow: function() {
        this._resetUIState();
    },

    /**
     * Reset the UI to initial state
     */
    _resetUIState: function() {
        // Clear intervals first
        this._clearIntervals();
        this.orderRef = null;
        this.currentQrContent = null;

        // Reset all UI elements to initial state
        this.$('#bankid_init_view').show();
        this.$('#bankid_init_footer').show();
        this.$('#bankid_signing_view').hide();
        this.$('#bankid_signing_footer').hide();

        // Reset init button
        this.$('#bankid_init_footer .bankid_sign_init').prop('disabled', false)
            .html('<i class="fa fa-pencil"></i> Sign with BankID');

        // Reset cancel button
        this.$('#bankid_signing_footer .bankid_sign_cancel').prop('disabled', false)
            .html('<i class="fa fa-times"></i> Cancel');

        // Reset status message
        this.$('#bankid_status').removeClass('alert-success alert-danger')
            .addClass('alert-info')
            .text('Starting BankID...');

        // Clear QR code container
        const qrContainer = this.$('#qrcode-container')[0];
        if (qrContainer) {
            qrContainer.innerHTML = '';
        }

        // Clear SSN input
        this.$('input[name="ssn"]').val('');

        // Reset auto-start link
        this.$('#bankid-autostart-link').attr('href', '#');
    },

    /**
     * Handle when modal is closed
     */
    _onModalClosed: function() {
        // Clear intervals and reset state
        this._clearIntervals();
        this.orderRef = null;
        this.currentQrContent = null;
    },

    _onBankIdInit: async function(ev) {
        ev.preventDefault();

        // Use this.$() to ensure we're searching within the widget's element
        const $form = this.$('#bankid_sign');
        const $ssnInput = this.$('input[name="ssn"]');

        // Check if input exists before trying to get value
        if ($ssnInput.length === 0) {
            alert("Error: SSN input field not found. Please refresh the page and try again.");
            return;
        }

        const ssnValue = $ssnInput.val();

        // Check if ssnValue is defined
        if (ssnValue === undefined || ssnValue === null) {
            console.error("SSN value is undefined!");
            alert("Error: Could not read SSN value. Please refresh the page and try again.");
            return;
        }

        this.ssn = ssnValue.trim();
        this.res_id = $form.data('res-id');
        this.res_model = $form.data('res-model');
        this.access_token = $form.data('token');


        // Validate SSN format
        if (!this._isValidSSN(this.ssn)) {
            alert("Invalid SSN format! Please enter in YYYYMMDD-NNNN format.");
            return;
        }

        // Disable button and show loading
        const $button = this.$('#bankid_init_footer .bankid_sign_init');
        $button.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Initializing...');

        try {
            // Initialize BankID
            const result = await rpc('/bankid/initialize', {
                res_id: this.res_id,
                res_model: this.res_model,
                ssn: this.ssn,
                access_token: this.access_token
            });

            if (result.error) {
                // Show error
                alert(result.error);
                $button.prop('disabled', false).html('<i class="fa fa-pencil"></i> Sign with BankID');
                return;
            }

            // Store order reference
            this.orderRef = result.order_ref;

            // Switch to signing view
            this.$('#bankid_init_view').hide();
            this.$('#bankid_init_footer').hide();
            this.$('#bankid_signing_view').show();
            this.$('#bankid_signing_footer').show();

            // Set auto-start link
            this.$('#bankid-autostart-link').attr(
                'href',
                'bankid:///?autostarttoken=' + result.auto_start_token
            );

            // Create initial QR code
            if (window.QRCode && result.qr_content) {
                this._generateQRCode(result.qr_content);

                // Start QR code updates immediately
                this._startQRUpdates();
            } else {
                console.warn("QRCode library not available or no QR content");
            }

            // Start polling for status
            this._startStatusPolling();

            // Initial status check
            this._checkStatus();

        } catch (error) {
            console.error("BankID initialization error:", error);
            alert("Error initializing BankID. Please try again.");
            $button.prop('disabled', false).html('<i class="fa fa-pencil"></i> Sign with BankID');
        }
    },

    _onBankIdCancel: async function(ev) {
        ev.preventDefault();

        // Check if this is the header close button or footer cancel button
        const isHeaderClose = $(ev.target).hasClass('btn-close') || $(ev.target).parent().hasClass('btn-close');

        if (isHeaderClose) {
            // If it's the header close button and we have an active order, prevent closing
            if (this.orderRef) {
                ev.stopPropagation();
                alert("Please cancel the BankID process using the Cancel button below, or complete the signing.");
                return;
            }
            // If no active order, allow closing
            return;
        }

        // This is the footer cancel button
        const $button = this.$('#bankid_signing_footer .bankid_sign_cancel');
        $button.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Cancelling...');

        if (this.orderRef) {
            try {
                await rpc('/bankid/cancel', {
                    order_ref: this.orderRef
                });

                // Clear intervals
                this._clearIntervals();
                this.orderRef = null;

                // Close modal
                this.$el.modal('hide');

            } catch (error) {
                console.error("BankID cancellation error:", error);
                alert("Error cancelling BankID process. Please try again.");
                $button.prop('disabled', false).html('<i class="fa fa-times"></i> Cancel');
            }
        } else {
            // Just close the modal if orderRef is not set
            this.$el.modal('hide');
        }
    },

    _startQRUpdates: function() {
        // Clear any existing interval
        if (this.qrInterval) {
            clearInterval(this.qrInterval);
        }

        // Update QR code every 1 second
        this.qrInterval = setInterval(() => {
            this._updateQRCode();
        }, 1000);

    },

    _startStatusPolling: function() {
        // Clear any existing interval
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
        }

        // Check status every 2 seconds
        this.statusInterval = setInterval(() => {
            this._checkStatus();
        }, 2000);

    },

    _updateQRCode: async function() {
        if (!this.orderRef) return;

        try {
            const result = await rpc('/bankid/get_qr', {
                res_id: this.res_id,
                res_model: this.res_model,
                ssn: this.ssn,
                access_token: this.access_token
            });

            if (result.error) {
                console.error("Error getting QR code:", result.error);
                return;
            }

            if (result.qr_content && this.currentQrContent !== result.qr_content) {
                this._generateQRCode(result.qr_content);
            }
        } catch (error) {
            console.error("Error updating QR code:", error);
        }
    },

    _generateQRCode: function(qrContent) {
        if (!qrContent) {
            console.warn("No QR content provided");
            return;
        }

        const qrContainer = this.$('#qrcode-container')[0];
        if (qrContainer && window.QRCode) {
            // Clear container
            qrContainer.innerHTML = '';

            try {
                // Generate new QR code
                new QRCode(qrContainer, {
                    text: qrContent,
                    width: 200,
                    height: 200,
                    colorDark: "#000000",
                    colorLight: "#ffffff",
                    correctLevel: QRCode.CorrectLevel.M
                });

                // Update current content
                this.currentQrContent = qrContent;
                console.log("QR code generated successfully");
            } catch (error) {
                console.error("Error creating QR code:", error);
            }
        } else {
            console.warn("QR container or QRCode library not available");
        }
    },

    _checkStatus: async function() {
        if (!this.orderRef) return;

        try {
            const result = await rpc('/bankid/collect', {
                res_id: this.res_id,
                res_model: this.res_model,
                access_token: this.access_token
            });

            const $statusEl = this.$('#bankid_status');

            if (result.status === 'complete') {
                // Clear intervals
                this._clearIntervals();

                // Show success message
                $statusEl.removeClass('alert-info alert-danger')
                    .addClass('alert-success')
                    .text('Signing completed successfully!');

                // Redirect after a delay
                setTimeout(() => {
                    window.location.reload();
                }, 2000);

            } else if (result.status === 'failed') {
                // Clear intervals
                this._clearIntervals();

                // Show failed message
                $statusEl.removeClass('alert-info')
                    .addClass('alert-danger')
                    .text('Signing failed: ' + (result.hintCode || 'Unknown error'));

                // Reset after a delay
                setTimeout(() => {
                    this._resetUIState();
                }, 3000);

            } else if (result.status === 'pending') {
                // Update hint message based on hint code
                let hintMessage = 'Waiting for BankID...';

                switch (result.hintCode) {
                    case 'outstandingTransaction':
                        hintMessage = 'Please open your BankID app';
                        break;
                    case 'noClient':
                        hintMessage = 'Start your BankID app';
                        break;
                    case 'started':
                        hintMessage = 'Authentication/signing in progress';
                        break;
                    case 'userSign':
                        hintMessage = 'Please check your BankID app and sign';
                        break;
                }

                $statusEl.text(hintMessage);
            } else {
                // Clear intervals
                this._clearIntervals();

                // Show error message
                $statusEl.removeClass('alert-info')
                    .addClass('alert-danger')
                    .text('Error: ' + (result.message || 'Unknown error'));
            }
        } catch (error) {
            console.error("Error checking status:", error);

            // Clear intervals
            this._clearIntervals();

            // Show error message
            this.$('#bankid_status')
                .removeClass('alert-info')
                .addClass('alert-danger')
                .text('Error checking status');
        }
    },

    _clearIntervals: function() {
        if (this.qrInterval) {
            clearInterval(this.qrInterval);
            this.qrInterval = null;
        }
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
            this.statusInterval = null;
        }
    },

    _isValidSSN: function(ssn) {
        const ssnPattern = /^(19|20)?\d{6}-\d{4}$/;
        return ssnPattern.test(ssn);
    }
});

export default publicWidget.registry.BankIDSignWidget;