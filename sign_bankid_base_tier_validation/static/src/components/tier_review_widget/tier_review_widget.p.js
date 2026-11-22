/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {ReviewsTable} from "@base_tier_validation/components/tier_review_widget/tier_review_widget.esm";

// Patch the existing component
patch(ReviewsTable.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },

    _getReviewData() {
        const records = this.env.model.root.data.review_ids.records;
        return records.map((record) => {
            // Include the ID in the returned data
            return {
                ...record.data,
                id: record.resId || record.data.id || record.id  // Try different sources for ID
            };
        });
    },


    async onViewDetails(ev, review) {
        ev.preventDefault();
        ev.stopPropagation();

        try {
            // Get the current record ID and model
            const recordId = this.env.model.root.data.id;
            const recordModel = this.env.model.root.resModel;

            if (review.id) {
                this.action.doAction({
                    type: 'ir.actions.act_window',
                    name: 'Review Details',
                    res_model: 'tier.review',
                    res_id: review.id,
                    views: [[false, 'form']],
                    target: 'new',
                });
            } else {
                console.error('No review ID found in:', review);
            }

        } catch (error) {
            console.error('Error opening view details:', error);
        }
    }
});

// Don't change the template here - use template inheritance instead