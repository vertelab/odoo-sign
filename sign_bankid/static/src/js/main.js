import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';


publicWidget.registry.BankIDSignWidget = publicWidget.Widget.extend({
    selector: '.modal-content',
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
    },

    start: function() {
        const result = this._super(...arguments);
        console.log("BankID Sign Widget Started");

        // Configure modal to not close on outside click or escape
        $('#modal_bankid_ssn').modal({
            backdrop: 'static',
            keyboard: false
        });

        $(document).on('hidden.bs.modal', '#modal_bankid_ssn', this._onModalClosed.bind(this));
        return result;
    },

    /**
     * Reset UI state when modal is shown
     */
    _onModalShow: function() {
        console.log("BankID modal opening - resetting state");
        this._resetUIState();
    },

    /**
     * Reset the UI to initial state
     */
    _resetUIState: function() {
        // Clear intervals first
        this._clearIntervals();
        this.orderRef = null;

        // Reset all UI elements to initial state

        // Show initial view, hide signing view
        this.$el.find('#bankid_init_view').show();
        this.$el.find('#bankid_init_footer').show();
        this.$el.find('#bankid_signing_view').hide();
        this.$el.find('#bankid_signing_footer').hide();

        // Reset init button (only the footer one, not the header close button)
        this.$el.find('#bankid_init_footer .bankid_sign_init').prop('disabled', false)
            .html('<i class="fa fa-pencil"></i> Sign with BankID');

        // Reset cancel button in footer (not the header close button)
        this.$el.find('#bankid_signing_footer .bankid_sign_cancel').prop('disabled', false)
            .html('<i class="fa fa-times"></i> Cancel');

        // Reset status message
        this.$el.find('#bankid_status').removeClass('alert-success alert-danger')
            .addClass('alert-info')
            .text('Starting BankID...');

        // Clear QR code container
        const qrContainer = this.$el.find('#qrcode-container')[0];
        if (qrContainer) {
            qrContainer.innerHTML = '';
        }

        // Clear SSN input
        this.$el.find('input[name="ssn"]').val('');

        // Reset auto-start link
        this.$el.find('#bankid-autostart-link').attr('href', '#');

        console.log("UI state reset complete");
    },

    /**
     * Handle when modal is closed
     */
    _onModalClosed: function() {
        console.log("BankID modal closed");

        // Clear intervals and reset state
        this._clearIntervals();
        this.orderRef = null;
    },

    _onBankIdInit: async function(ev) {
        ev.preventDefault();
        console.log("BankID Init triggered");

        const $form = this.$el.find('#bankid_sign');
        const ssnValue = $form.find('input[name="ssn"]').val().trim();
        const orderId = $form.data('order-id');
        const accessToken = $form.data('token');

        // Validate SSN format
        if (!this._isValidSSN(ssnValue)) {
            alert("Invalid SSN format! Please enter in YYYYMMDD-NNNN format.");
            return;
        }

        // Disable button and show loading (only the footer button)
        const $button = this.$el.find('#bankid_init_footer .bankid_sign_init');
        $button.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Initializing...');

        try {
            // Initialize BankID
            const result = await rpc('/bankid/initialize', {
                order_id: orderId,
                ssn: ssnValue,
                access_token: accessToken
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
            this.$el.find('#bankid_init_view').hide();
            this.$el.find('#bankid_init_footer').hide();
            this.$el.find('#bankid_signing_view').show();
            this.$el.find('#bankid_signing_footer').show();

            // Set auto-start link
            this.$el.find('#bankid-autostart-link').attr(
                'href',
                'bankid:///?autostarttoken=' + result.auto_start_token
            );

            console.log('qr code', result.qr_content)

            // Create QR code
            if (window.QRCode) {
                console.log("Creating QR code")
                const qrContainer = this.$el.find('#qrcode-container')[0];
                qrContainer.innerHTML = ''; // Clear container

                new QRCode(qrContainer, {
                    text: result.qr_content,
                    width: 200,
                    height: 200
                });

                // Update QR code every second
                this.qrInterval = setInterval(() => {
                    this._updateQRCode();
                }, 1000);
            }

            // Start polling for status
            this.statusInterval = setInterval(() => {
                this._checkStatus();
            }, 2000);

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
        console.log("BankID Cancel triggered");

        // Check if this is the header close button or footer cancel button
        const isHeaderClose = $(ev.target).hasClass('btn-close');

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
        const $button = this.$el.find('#bankid_signing_footer .bankid_sign_cancel');
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
                $('#modal_bankid_ssn').modal('hide');

            } catch (error) {
                console.error("BankID cancellation error:", error);
                alert("Error cancelling BankID process. Please try again.");
                $button.prop('disabled', false).html('<i class="fa fa-times"></i> Cancel');
            }
        } else {
            // Just close the modal if orderRef is not set
            $('#modal_bankid_ssn').modal('hide');
        }
    },

    _updateQRCode: async function() {
        if (!this.orderRef) return;

        try {
            const qrContent = await rpc('/bankid/get_qr', {
                order_ref: this.orderRef
            });

            console.log("New QR Content:", qrContent); // Debug log

            if (qrContent && this.currentQrContent !== qrContent) {
                this.currentQrContent = qrContent; // Track current content

                // Update QR code
                const qrContainer = this.$el.find('#qrcode-container')[0];
                qrContainer.innerHTML = ''; // Clear container

                new QRCode(qrContainer, {
                    text: qrContent,
                    width: 200,
                    height: 200
                });

                console.log("QR Code updated!"); // Debug log
            }
        } catch (error) {
            console.error("Error updating QR code:", error);
        }
    },

    _checkStatus: async function() {
        if (!this.orderRef) return;

        try {
            const result = await rpc('/bankid/collect', {
                order_ref: this.orderRef
            });

            const $statusEl = this.$el.find('#bankid_status');

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
                    window.location.reload();
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
            this.$el.find('#bankid_status')
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