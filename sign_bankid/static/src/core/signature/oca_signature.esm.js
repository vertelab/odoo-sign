/** @odoo-module **/

// sign_oca module

import {SignatureDialog} from "@web/core/signature/signature_dialog";
import {registry} from "@web/core/registry";
import {renderToString} from "@web/core/utils/render";

import {patch} from "@web/core/utils/patch";

// Patch the existing signature handler
patch(registry.category("sign_oca").get("signature"), {
    generate: function (parent, item, signatureItem) {
        var input = $(
            renderToString("sign_oca.sign_iframe_field_signature", {item: item})
        )[0];

        if (item.role_id === parent.info.role_id) {
            signatureItem[0].addEventListener("focus_signature", () => {
                var signatureOptions = {
                    nameAndSignatureProps: {fontColor: "DarkBlue"},
                    defaultName: parent.info.partner.name,
                    // Just spread all the info data
                    ...parent.info
                };
                parent.dialogService.add(SignatureDialog, {
                    ...signatureOptions,
                    uploadSignature: (data) =>
                        this.uploadSignature(parent, item, signatureItem, data),
                });
            });
            input.addEventListener("click", (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                var signatureOptions = {
                    nameAndSignatureProps: {fontColor: "DarkBlue"},
                    defaultName: parent.info.partner.name,
                    // Just spread all the info data
                    ...parent.info
                };
                parent.dialogService.add(SignatureDialog, {
                    ...signatureOptions,
                    uploadSignature: (data) =>
                        this.uploadSignature(parent, item, signatureItem, data),
                });
            });
            input.addEventListener("keydown", (ev) => {
                if ((ev.keyCode || ev.which) !== 9) {
                    return true;
                }
                ev.preventDefault();
                var next_items = Object.values(parent.info.items).filter(
                    (i) =>
                        i.tabindex > item.tabindex && i.role_id === parent.info.role_id
                );
                if (next_items.length > 0) {
                    ev.currentTarget.blur();
                    parent.items[next_items[0].id].dispatchEvent(
                        new Event("focus_signature")
                    );
                }
            });
        }
        return input;
    },
});