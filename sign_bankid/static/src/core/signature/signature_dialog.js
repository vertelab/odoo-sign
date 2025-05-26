// web SignatureDialog patch
import { SignatureDialog } from "@web/core/signature/signature_dialog";
import { BankIDSignature } from "./bankid_signature";
import { patch } from "@web/core/utils/patch";

// Patch the SignatureDialog to add BankID functionality
patch(SignatureDialog.prototype, {
    /**
     * Handle BankID signature completion
     */
    onBankIDComplete(signatureData) {
        this.props.uploadSignature(signatureData);
        this.props.close();
    },

    /**
     * Get props for BankID component
     */
    get bankIDSignatureProps() {
        // Since we're spreading parent.info, all the data is in props
        // Just pass what BankID needs from the props
//        return {
//            resModel: this.props.res_model,
//            resId: this.props.res_id,
//            accessToken: this.props.access_token,
//            partner: this.props.partner,
//            signingOption: this.props.signing_option,
//            uploadSignature: this.onBankIDComplete.bind(this),
//            close: this.props.close,
//        };
        return {
            document_id: this.props.document_id,  // The sign.oca.request.signer ID
            access_token: this.props.access_token,
            partner: this.props.partner,
            signingOption: this.props.signing_option,
            uploadSignature: this.onBankIDComplete.bind(this),
            close: this.props.close,
        };
    },

    /**
     * Override confirm to only work for draw method
     */
    onClickConfirm() {
        if (this.props.signingOption !== 'bankid') {
            super.onClickConfirm();
        }
    }
});

// Add BankIDSignature to the components
SignatureDialog.components = {
    ...SignatureDialog.components,
    BankIDSignature
};

// Extend props to include BankID specific ones
SignatureDialog.props = {
    ...SignatureDialog.props,
    // These will come from spreading parent.info
    document_id: { type: Number, optional: true },
    signing_option: { type: String, optional: true },
    res_model: { type: String, optional: true },
    res_id: { type: Number, optional: true },
    access_token: { type: String, optional: true },
    partner: { type: Object, optional: true },
    role_id: { type: Number, optional: true },
    items: { type: Object, optional: true },
    to_sign: { type: Boolean, optional: true },
    ask_location: { type: Boolean, optional: true },
};