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
        this.callbackMethod = this.props.context?.callback_method;
        this.isDestroyed = false;

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

        // Cleanup intervals when component is unmounted
        onWillUnmount(() => {
            this.isDestroyed = true;
            this.stopPolling();
            this.stopQRUpdates();
        });
    }

    async startBankIDSigning() {
        try {
            this.state.status = 'signing';
            this.state.message = 'Initiating BankID signing...';

            const result = await this.orm.call(
                this.recordModel,
                'initiate_bankid_client',
                [this.recordId]
            );

            if (this.isDestroyed) {
                return;
            }

            if (result.success) {
                this.state.orderRef = result.orderRef;
                this.state.qrCode = result.qrCode;
                this.state.autoStartUrl = result.autoStartUrl;
                this.state.message = 'Please sign using your BankID app';

                setTimeout(() => {
                    if (!this.isDestroyed) {
                        this.generateQRCode();
                    }
                }, 100);

                this.startQRUpdates();
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

    async handleSigningComplete() {
        this.state.status = 'complete';
        this.state.message = 'Document signed successfully!';
        this.stopPolling();
        this.stopQRUpdates();

        // If there's a callback method, call it
        if (this.callbackMethod) {
            try {
                console.log(`Calling callback method: ${this.callbackMethod} on ${this.recordModel}[${this.recordId}]`);

                const result = await this.orm.call(
                    this.recordModel,
                    this.callbackMethod,
                    [this.recordId]
                );

                console.log('Callback result:', result);

                // Check if callback returned an error
                if (result && typeof result === 'object' && result.success === false) {
                    throw new Error(result.error || 'Callback returned failure');
                }

                // Show success notification
                this.notification.add('Document signed and validated successfully!', {
                    type: 'success'
                });

                // Close modal first
                this.props.close();

                // Then reload to show updated state
                setTimeout(() => {
                    window.location.reload();
                }, 1000);

            } catch (error) {
                console.error('Error calling callback method:', error);
                console.error('Full error details:', {
                    message: error.message,
                    data: error.data,
                    stack: error.stack
                });

                this.notification.add(
                    `Signing completed but validation failed: ${error.message}`,
                    { type: 'warning' }  // Changed to warning since signing did work
                );

                // Still close the modal
                this.props.close();

                // Still reload to show that signing worked
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        } else {
            console.log('No callback method specified, just closing modal');

            // Show success notification
            this.notification.add('Document signed successfully!', {
                type: 'success'
            });

            // Close modal
            this.props.close();

            // Reload after delay
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        }
    }

    startPolling() {
        this.stopPolling();

        this.pollInterval = setInterval(async () => {
            if (this.isDestroyed) {
                this.stopPolling();
                return;
            }

            try {
                const status = await this.orm.call(
                    this.recordModel,
                    'check_bankid_status',
                    [this.recordId]
                );

                if (this.isDestroyed) {
                    console.log('Component destroyed during polling, aborting');
                    return;
                }

                console.log('BankID status:', status);

                if (status.status === 'complete') {
                    // Just call handleSigningComplete - it handles everything
                    await this.handleSigningComplete();
                } else if (status.status === 'failed') {
                    this.state.status = 'error';
                    this.state.message = status.message || 'BankID signing failed';
                    this.stopPolling();
                    this.stopQRUpdates();
                } else if (status.hintCode) {
                    // Update message based on hint code for better UX
                    this.updateMessageFromHintCode(status.hintCode);
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
        }, 2000);
    }

    updateMessageFromHintCode(hintCode) {
        const messages = {
            'outstandingTransaction': 'Please complete the signing in your BankID app',
            'noClient': 'BankID app not found. Please install the BankID app and try again',
            'userCancel': 'Signing was cancelled by user',
            'cancelled': 'Signing was cancelled',
            'expiredTransaction': 'Signing session expired. Please try again',
            'certificateErr': 'Certificate error. Please try again',
            'userDeclinedCall': 'User declined the call',
            'timeout': 'Signing timed out. Please try again',
            'prematurely_completed': 'Signing completed prematurely',
            'unknown_error': 'Unknown error occurred'
        };

        if (messages[hintCode]) {
            this.state.message = messages[hintCode];
        }
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    startQRUpdates() {
        this.stopQRUpdates();

        this.qrUpdateInterval = setInterval(async () => {
            if (this.isDestroyed) {
                this.stopQRUpdates();
                return;
            }

            try {
                const result = await this.orm.call(
                    this.recordModel,
                    'get_updated_qr_code',
                    [this.recordId]
                );

                if (this.isDestroyed) {
                    console.log('Component destroyed during QR update, aborting');
                    return;
                }

                if (result.success && result.qrCode && result.qrCode !== this.state.qrCode) {
                    this.state.qrCode = result.qrCode;
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
        }, 1000);
    }

    stopQRUpdates() {
        if (this.qrUpdateInterval) {
            clearInterval(this.qrUpdateInterval);
            this.qrUpdateInterval = null;
        }
    }

    async cancelSigning() {
        try {
            this.stopPolling();
            this.stopQRUpdates();
            this.isDestroyed = true;

            this.state.status = 'cancelling';
            this.state.message = 'Cancelling BankID signing...';

            await this.orm.call(
                this.recordModel,
                'cancel_bankid_sign',
                [this.recordId]
            );

            console.log('BankID signing cancelled successfully');
            this.props.close();

        } catch (error) {
            console.error('Error cancelling BankID signing:', error);
            this.notification.add('Error cancelling BankID signing: ' + error.message, { type: 'danger' });
            this.props.close();
        }
    }

    generateQRCode() {
        if (this.isDestroyed) {
            console.log('Component destroyed, skipping QR generation');
            return;
        }

        if (!this.state.qrCode) {
            console.warn('No QR code content available');
            return;
        }

        const container = document.getElementById('qrcode-container');
        if (container && window.QRCode) {
            container.innerHTML = '';

            try {
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