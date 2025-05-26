import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

console.log("SignBankID Loaded");

publicWidget.registry.BankIDSignWidget = publicWidget.Widget.extend({
    selector: '.modal',
    events: {
        'click .bankid_sign_init': '_onBankIdInit',
    },

    _onBankIdInit: async function (ev) {
        ev.preventDefault();
        console.log("_onBankIDSubmitRequest triggered");

        var $form = this.$el.find('#bankid_sign');
        var ssnValue = $form.find('input[name="ssn"]').val().trim();
        var orderId = $form.attr('data-order-id');
        var accessToken = $form.attr('data-token');
        var partner = this.$el.find('[t-field="sale_order.partner_id.commercial_partner_id"]').text().trim();

        // Debug: Log values before sending
        console.log("Extracted Values:");
        console.log("SSN:", ssnValue);
        console.log("Order ID:", orderId);
        console.log("Access Token:", accessToken);
        console.log("Partner:", partner);

        // Validate SSN format
        if (!this._isValidSSN(ssnValue)) {
            alert("Invalid SSN format! Please enter in YYYYMMDD-NNNN format.");
            return;
        }

        // Send the RPC request
        try {
            let response = await rpc('/knowit/bankid/sign/init', {
                order_id: orderId,
                access_token: accessToken,
                partner: partner,
                ssn: ssnValue
            });

            console.log("RPC Response:", response);

            if (response.success) {
                alert("Sign request successful!");
//                location.reload();
            } else {
                alert("Sign request failed: " + response.message);
            }
        } catch (error) {
            console.error("RPC Error:", error);
            alert("An error occurred while processing the sign request.");
        }
    },

    _isValidSSN: function (ssn) {
        var ssnPattern = /^(19|20)?\d{6}-\d{4}$/;
        return ssnPattern.test(ssn);
    }
});

// Register widget
publicWidget.registry.BankIDSignWidget;
