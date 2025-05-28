// static/src/js/bankid_modal.js
/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BankIDSignModal extends Component {
    static template = "sign_bankid.BankIDSignModal";
    static components = { Dialog };
    static props = {
        close: Function,
        context: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            status: 'idle', // idle, signing, complete, error
            qrCode: '',
            autoStartUrl: '',
            message: '',
            orderRef: '',
        });

        this.pollInterval = null;
        this.qrUpdateInterval = null;
        this.recordId = this.props.context?.default_record_id;
        this.recordModel = this.props.context?.default_record_model;
        this.isDestroyed = false; // Add flag to track component state

        console.log('BankID Modal Setup:', {
            recordId: this.recordId,
            recordModel: this.recordModel,
            fullContext: this.props.context
        });

        // Validate that we have the required context
        if (!this.recordId || !this.recordModel) {
            console.error('Missing required context:', {
                recordId: this.recordId,
                recordModel: this.recordModel,
                context: this.props.context
            });
            this.state.status = 'error';
            this.state.message = 'Missing record information. Please close and try again.';
        }

        // Auto-start BankID when modal is mounted
//        onMounted(() => {
//            console.log('BankID Modal mounted - auto-starting BankID signing');
//            // Only auto-start if we have valid context
//            if (this.recordId && this.recordModel && this.state.status !== 'error') {
//                this.startBankIDSigning();
//            }
//        });

        // Cleanup intervals when component is unmounted
        onWillUnmount(() => {
            console.log('BankID Modal unmounting - cleaning up intervals');
            this.isDestroyed = true;
            this.stopPolling();
            this.stopQRUpdates();
        });
    }

    async startBankIDSigning() {
        try {
            this.state.status = 'signing';
            this.state.message = 'Initiating BankID signing...';

            console.log('Starting BankID signing for:', {
                recordId: this.recordId,
                recordModel: this.recordModel,
                context: this.props.context
            });

            // Call your backend method to start BankID signing
            const result = await this.orm.call(
                this.recordModel,
                'initiate_bankid_client',
                [this.recordId]
            );

            console.log('BankID initiation result:', result);

            // Check if component was destroyed while waiting for response
            if (this.isDestroyed) {
                console.log('Component destroyed during initiation, aborting');
                return;
            }

            if (result.success) {
                this.state.orderRef = result.orderRef;
                this.state.qrCode = result.qrCode;
                this.state.autoStartUrl = result.autoStartUrl;
                this.state.message = 'Please sign using your BankID app';

                // Generate initial QR code after state update
                setTimeout(() => {
                    if (!this.isDestroyed) {
                        this.generateQRCode();
                    }
                }, 100);

                // Start QR code updates every 1 second
                this.startQRUpdates();

                // Start polling for completion
                this.startPolling();
            } else {
                this.state.status = 'error';
                this.state.message = result.error || 'Failed to start BankID signing';
            }
        } catch (error) {
            console.error('Error starting BankID:', error);
            if (!this.isDestroyed) {
                this.state.status = 'error';
                this.state.message = 'Error starting BankID signing: ' + error.message;
            }
        }
    }

    startPolling() {
        // Clear any existing interval
        this.stopPolling();

        this.pollInterval = setInterval(async () => {
            // Check if component is destroyed before making RPC call
            if (this.isDestroyed) {
                console.log('Component destroyed, stopping polling');
                this.stopPolling();
                return;
            }

            try {
                console.log(`Polling BankID status for ${this.recordModel} ID ${this.recordId}`);

                const status = await this.orm.call(
                    this.recordModel,
                    'check_bankid_status',
                    [this.recordId]
                );

                // Check again after async call
                if (this.isDestroyed) {
                    console.log('Component destroyed during polling, aborting');
                    return;
                }

                console.log('BankID status response:', status);

                if (status.status === 'complete') {
                    this.state.status = 'complete';
                    this.state.message = 'Document signed successfully!';
                    this.stopPolling();
                    this.stopQRUpdates();

                    setTimeout(() => {
                        if (!this.isDestroyed) {
                            this.props.close();
                            // Reload the form view to show updated data
                            window.location.reload();
                        }
                    }, 2000);
                } else if (status.status === 'failed') {
                    this.state.status = 'error';
                    this.state.message = status.message || 'BankID signing failed';
                    this.stopPolling();
                    this.stopQRUpdates();
                }
            } catch (error) {
                console.error('Polling error:', error);
                if (!this.isDestroyed) {
                    this.state.status = 'error';
                    this.state.message = 'Error checking BankID status: ' + error.message;
                    this.stopPolling();
                    this.stopQRUpdates();
                }
            }
        }, 2000); // Poll every 2 seconds
    }

    stopPolling() {
        if (this.pollInterval) {
            console.log('Stopping polling interval');
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    startQRUpdates() {
        // Clear any existing interval
        this.stopQRUpdates();

        // Update QR code every 1 second for BankID time-based authentication
        this.qrUpdateInterval = setInterval(async () => {
            // Check if component is destroyed before making RPC call
            if (this.isDestroyed) {
                console.log('Component destroyed, stopping QR updates');
                this.stopQRUpdates();
                return;
            }

            try {
                console.log(`Updating QR for ${this.recordModel} ID ${this.recordId}`);

                const result = await this.orm.call(
                    this.recordModel,
                    'get_updated_qr_code',
                    [this.recordId]
                );

                // Check again after async call
                if (this.isDestroyed) {
                    console.log('Component destroyed during QR update, aborting');
                    return;
                }

                console.log('QR update result:', result);

                if (result.success && result.qrCode && result.qrCode !== this.state.qrCode) {
                    console.log('QR code updated');
                    this.state.qrCode = result.qrCode;
                    // Generate QR code with a small delay to ensure state is updated
                    setTimeout(() => {
                        if (!this.isDestroyed) {
                            this.generateQRCode();
                        }
                    }, 50);
                }
            } catch (error) {
                if (!this.isDestroyed) {
                    console.error('QR update error:', error);
                }
            }
        }, 1000); // Update every second
    }

    stopQRUpdates() {
        if (this.qrUpdateInterval) {
            console.log('Stopping QR update interval');
            clearInterval(this.qrUpdateInterval);
            this.qrUpdateInterval = null;
        }
    }

    async cancelSigning() {
        try {
            console.log('Cancelling BankID signing...');

            // Stop intervals immediately
            this.stopPolling();
            this.stopQRUpdates();

            // Set flag to prevent further operations
            this.isDestroyed = true;

            // Update state to show cancelling
            this.state.status = 'cancelling';
            this.state.message = 'Cancelling BankID signing...';

            // Call cancel on backend
            await this.orm.call(
                this.recordModel,
                'cancel_bankid_sign',
                [this.recordId]
            );

            console.log('BankID signing cancelled successfully');

            // Close the modal
            this.props.close();

        } catch (error) {
            console.error('Error cancelling BankID signing:', error);
            this.notification.add('Error cancelling BankID signing: ' + error.message, { type: 'danger' });

            // Still close the modal even if cancel fails
            this.props.close();
        }
    }

    generateQRCode() {
        // Check if component is destroyed
        if (this.isDestroyed) {
            console.log('Component destroyed, skipping QR generation');
            return;
        }

        console.log('generateQRCode called with:', {
            qrCode: this.state.qrCode,
            qrCodeLength: this.state.qrCode ? this.state.qrCode.length : 0,
            hasQRCodeLib: !!window.QRCode
        });

        if (!this.state.qrCode) {
            console.warn('No QR code content available');
            return;
        }

        const container = document.getElementById('qrcode-container');
        if (container && window.QRCode) {
            // Clear any existing QR code
            container.innerHTML = '';

            try {
                // Generate new QR code
                new QRCode(container, {
                    text: this.state.qrCode,
                    width: 200,
                    height: 200,
                    colorDark: "#000000",
                    colorLight: "#ffffff",
                    correctLevel: QRCode.CorrectLevel.M
                });
                console.log('QR code generated successfully');
            } catch (error) {
                console.error('Error generating QR code:', error);
                if (container) {
                    container.innerHTML = '<p class="text-danger">Error generating QR code</p>';
                }
            }
        } else {
            console.warn('QRCode library not loaded or container not found', {
                hasContainer: !!container,
                hasQRCode: !!window.QRCode
            });
        }
    }
}

// Register the action
registry.category("actions").add("bankid_sign_modal", (env, action) => {
    env.services.dialog.add(BankIDSignModal, {
        context: action.context,
    });
});