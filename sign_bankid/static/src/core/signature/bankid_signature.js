// BankIDSignature Component
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpc } from "@web/core/network/rpc";
import { Component, useState, onWillStart, useRef } from "@odoo/owl";


export class BankIDSignature extends Component {
    static template = "sign_bankid.BankIDSignature";
    static components = { Dropdown, DropdownItem };

    setup() {
        super.setup();

        this.state = useState({
            bankidInitiated: false,
            bankidStatus: 'Ready to start BankID',
            bankidData: null,
            bankidSSN: '',
            bankidOrderRef: null,
            ssnError: '',
            statusClass: 'alert-info'
        });
    }

    /**
     * Initiate BankID signing process
     */
    async initiateBankID() {
        try {
            if (!this.state.bankidSSN) {
                alert('Please enter personal number');
                return
            }

            // Send only what the controller expects
            const result = await rpc('/bankid/initialize', {
                document_id: this.props.document_id,
                ssn: this.state.bankidSSN.trim(),
                access_token: this.props.access_token
            });

            if (result.error) {
                this.state.bankidStatus = `Error: ${result.error}`;
                this.state.bankidInitiated = false;
                alert(this.state.bankidStatus);
                return
            }

            this.state.bankidInitiated = true;

            // Store BankID data
            this.state.bankidData = {
                orderRef: result.order_ref,
                autoStartUrl: `bankid:///?autostarttoken=${result.auto_start_token}`,
                qrContent: result.qr_content
            };
            this.state.bankidOrderRef = result.order_ref;

            // Generate QR code after a short delay to ensure DOM is updated
            setTimeout(() => {
                this.generateQRCode(result.qr_content);
            }, 100);

            // Start polling for status
            this.startBankIDPolling();

        } catch (error) {
            console.error('BankID initialization error:', error);
            this.state.bankidStatus = error.error || error.message || 'Error initializing BankID';
            this.state.statusClass = 'alert-danger';

            // If initialization fails, go back to input view
            this.state.bankidInitiated = false;
            this.state.ssnError = error.error || error.message || 'Error initializing BankID';
        }
    }

    /**
     * Generate QR code for BankID
     */
    generateQRCode(qrContent) {
        const container = document.getElementById('qrcode-container');
        if (container && window.QRCode) {
            container.innerHTML = '';
            new QRCode(container, {
                text: qrContent,
                width: 200,
                height: 200
            });
        }
    }

    /**
     * Start polling BankID status
     */
    startBankIDPolling() {
        if (this.bankidStatusInterval) {
            clearInterval(this.bankidStatusInterval);
        }

        if (this.bankidQRInterval) {
            clearInterval(this.bankidQRInterval);
        }

        // Poll status every 2 seconds
        this.bankidStatusInterval = setInterval(async () => {
            await this.checkBankIDStatus();
        }, 2000);

        // Update QR code every second
        this.bankidQRInterval = setInterval(async () => {
            await this.updateQRCode();
        }, 1000);
    }

    /**
     * Check BankID status
     */
    async checkBankIDStatus() {
        if (!this.state.bankidOrderRef) return;

        try {
            const result = await rpc('/bankid/collect', {
                order_ref: this.state.bankidOrderRef,
                access_token: this.props.access_token
            });

            if (result.status === 'complete') {
                this.clearBankIDIntervals();
                this.state.bankidStatus = 'Signing completed successfully!';

                // Complete the signing process
                this.completeBankIDSigning(result);

            } else if (result.status === 'failed') {
                this.clearBankIDIntervals();
                this.state.bankidStatus = `Signing failed: ${result.hintCode || 'Unknown error'}`;

            } else if (result.status === 'pending') {
                // Update status based on hint code
                this.updateBankIDStatus(result.hintCode);
            }
        } catch (error) {
            console.error('Error checking BankID status:', error);
            this.clearBankIDIntervals();
            this.state.bankidStatus = 'Error checking status';
        }
    }

    /**
     * Update QR code
     */
    async updateQRCode() {
        if (!this.state.bankidOrderRef) return;

        try {
            const result = await rpc('/bankid/get_qr', {
                order_ref: this.state.bankidOrderRef,
                access_token: this.props.access_token
            });

            if (result.qr_content) {
                this.generateQRCode(result.qr_content);
            }
        } catch (error) {
            console.error('Error updating QR code:', error);
        }
    }

    /**
     * Update BankID status message
     */
    updateBankIDStatus(hintCode) {
        const statusMessages = {
            'outstandingTransaction': 'Please open your BankID app',
            'noClient': 'Start your BankID app',
            'started': 'Authentication/signing in progress',
            'userSign': 'Please check your BankID app and sign',
        };

        this.state.bankidStatus = statusMessages[hintCode] || 'Waiting for BankID...';
    }

    /**
     * Complete BankID signing
     */
    completeBankIDSigning(result) {
        // Generate a signature image from BankID data
        const signatureData = this.generateBankIDSignatureImage(result);

        // Call the upload signature function
        this.props.uploadSignature({
            name: result.completionData?.user?.name || this.props.partner?.name || 'BankID User',
            signatureImage: signatureData,
            bankidData: result,
            res_model: this.props.resModel,
            res_id: this.props.resId
        });
    }

    /**
     * Generate signature image from BankID data
     */
    generateBankIDSignatureImage(result) {
        // Create a canvas to generate signature image
        const canvas = document.createElement('canvas');
        const scale = 3; // Increase for better quality
        canvas.width = 400 * scale;
        canvas.height = 250 * scale;

        const ctx = canvas.getContext('2d');
        ctx.scale(scale, scale); // Scale context to match

        // Fill background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw border
        ctx.strokeStyle = '#007bff';
        ctx.lineWidth = 2;
        ctx.strokeRect(2, 2, canvas.width - 4, canvas.height - 4);

        // Draw text
        ctx.fillStyle = '#000000';
        ctx.font = 'bold 18px Arial';
        ctx.fillText('Digitally Signed with BankID', 20, 30);

        // User info
        ctx.font = '14px Arial';
        const userData = result.completionData?.user || {};
        let y = 60; // Initial y position for user info
        const lineHeight = 22;

        ctx.fillText(`Name: ${userData.name || 'N/A'}`, 20, y);
        y += lineHeight;

        // Uncomment if personalNumber is needed
        // ctx.fillText(`Personal Number: ${userData.personalNumber || 'N/A'}`, 20, y);
        // y += lineHeight;

        ctx.fillText(`Role: ${userData.role || 'N/A'}`, 20, y);
        y += lineHeight;

        ctx.fillText(`Transaction ID: ${result.orderRef || 'N/A'}`, 20, y);
        y += lineHeight;

        ctx.fillText(`Date: ${new Date().toLocaleString()}`, 20, y);
        y += lineHeight;

        ctx.fillText('Method: BankID Digital Signature', 20, y);

        return canvas.toDataURL('image/png');
    }

    /**
     * Cancel BankID process
     */
    async cancelBankID() {
        if (this.state.bankidOrderRef) {
            try {
                await rpc('/bankid/cancel', {
                    order_ref: this.state.bankidOrderRef,
                    access_token: this.props.access_token
                });
            } catch (error) {
                console.error('Error cancelling BankID:', error);
            }
        }

        this.clearBankIDIntervals();
        this.state.bankidInitiated = false;
        this.state.bankidStatus = 'BankID cancelled';
        this.state.bankidOrderRef = null;
        this.state.ssnError = '';
        this.state.statusClass = 'alert-info';
        // Don't clear SSN so user doesn't have to re-enter it
    }

    /**
     * Clear BankID intervals
     */
    clearBankIDIntervals() {
        if (this.bankidStatusInterval) {
            clearInterval(this.bankidStatusInterval);
            this.bankidStatusInterval = null;
        }
        if (this.bankidQRInterval) {
            clearInterval(this.bankidQRInterval);
            this.bankidQRInterval = null;
        }
    }

    /**
     * Clean up on component destruction
     */
    willUnmount() {
        this.clearBankIDIntervals();
        super.willUnmount();
    }
}