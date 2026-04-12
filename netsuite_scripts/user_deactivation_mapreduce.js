/**
 * @NApiVersion 2.1
 * @NScriptType MapReduceScript
 * @NModuleScope SameAccount
 *
 * NetSuite User Deactivation Map/Reduce Script
 *
 * Handles bulk user deactivation (>10 users)
 * For small batches (<= 10 users), use RESTlet
 *
 * Script Parameters:
 * - custscript_user_ids_to_deactivate (Text) - Comma-separated user IDs
 * - custscript_deactivation_reason (Text) - Reason for deactivation
 * - custscript_requested_by (Text) - Who requested the deactivation
 * - custscript_dry_run (Checkbox) - Dry run mode (no changes made)
 */

define(['N/record', 'N/search', 'N/runtime', 'N/email'], function(record, search, runtime, email) {

    /**
     * getInputData stage
     * Returns users to deactivate
     */
    function getInputData() {
        const script = runtime.getCurrentScript();

        // Get script parameters
        const userIdsParam = script.getParameter({
            name: 'custscript_user_ids_to_deactivate'
        });

        const reason = script.getParameter({
            name: 'custscript_deactivation_reason'
        }) || 'Okta reconciliation';

        const requestedBy = script.getParameter({
            name: 'custscript_requested_by'
        }) || 'system';

        const dryRun = script.getParameter({
            name: 'custscript_dry_run'
        });

        if (!userIdsParam) {
            log.error('Missing Parameter', 'custscript_user_ids_to_deactivate is required');
            return [];
        }

        // Parse comma-separated IDs
        const userIds = userIdsParam.split(',')
            .map(id => id.trim())
            .filter(id => id);

        log.audit('Input Data', {
            total_users: userIds.length,
            reason: reason,
            requested_by: requestedBy,
            dry_run: dryRun === 'T' || dryRun === true
        });

        // Return as array of objects for map stage
        return userIds.map(id => ({
            id: id,
            reason: reason,
            requested_by: requestedBy,
            dry_run: dryRun === 'T' || dryRun === true
        }));
    }

    /**
     * map stage
     * Process each user
     */
    function map(context) {
        const userData = JSON.parse(context.value);
        const userId = userData.id;
        const reason = userData.reason;
        const requestedBy = userData.requested_by;
        const dryRun = userData.dry_run;

        try {
            // Load employee record
            const employeeRecord = record.load({
                type: record.Type.EMPLOYEE,
                id: userId
            });

            const email = employeeRecord.getValue({ fieldId: 'email' });
            const name = employeeRecord.getValue({ fieldId: 'entityid' });
            const currentStatus = employeeRecord.getValue({ fieldId: 'isinactive' });

            // Check if already inactive
            if (currentStatus === true || currentStatus === 'T') {
                log.audit('Already Inactive', {
                    user_id: userId,
                    name: name,
                    email: email
                });

                context.write({
                    key: 'success',
                    value: {
                        user_id: userId,
                        email: email,
                        name: name,
                        status: 'already_inactive',
                        message: 'User was already inactive'
                    }
                });
                return;
            }

            if (!dryRun) {
                // Set inactive
                employeeRecord.setValue({
                    fieldId: 'isinactive',
                    value: true
                });

                // Add note to comments field (if exists)
                try {
                    const currentComments = employeeRecord.getValue({ fieldId: 'comments' }) || '';
                    const timestamp = new Date().toISOString();
                    const newComment = `${timestamp} - Deactivated by ${requestedBy}. Reason: ${reason}`;
                    employeeRecord.setValue({
                        fieldId: 'comments',
                        value: currentComments + '\n' + newComment
                    });
                } catch (commentError) {
                    log.debug('Comment Update Failed', {
                        user_id: userId,
                        error: commentError.message
                    });
                }

                // Save
                employeeRecord.save();

                log.audit('User Deactivated', {
                    user_id: userId,
                    name: name,
                    email: email,
                    requested_by: requestedBy,
                    reason: reason
                });

                context.write({
                    key: 'success',
                    value: {
                        user_id: userId,
                        email: email,
                        name: name,
                        status: 'deactivated',
                        message: 'Successfully deactivated'
                    }
                });
            } else {
                // Dry run
                log.audit('Dry Run', {
                    user_id: userId,
                    name: name,
                    email: email,
                    current_status: currentStatus ? 'inactive' : 'active'
                });

                context.write({
                    key: 'success',
                    value: {
                        user_id: userId,
                        email: email,
                        name: name,
                        current_status: currentStatus ? 'inactive' : 'active',
                        status: 'dry_run',
                        message: 'Dry run - no changes made'
                    }
                });
            }

        } catch (e) {
            log.error('Deactivation Failed', {
                user_id: userId,
                error: e.message,
                error_name: e.name,
                stack: e.stack
            });

            context.write({
                key: 'failed',
                value: {
                    user_id: userId,
                    error: e.message,
                    error_code: e.name
                }
            });
        }
    }

    /**
     * reduce stage
     * Aggregate results by success/failed
     */
    function reduce(context) {
        const results = context.values.map(v => JSON.parse(v));

        // Store aggregated results
        context.write({
            key: context.key,
            value: results
        });
    }

    /**
     * summarize stage
     * Final results and notifications
     */
    function summarize(summary) {
        log.audit('Summary', 'Map/Reduce execution complete');

        let successCount = 0;
        let failedCount = 0;
        const successDetails = [];
        const failedDetails = [];

        // Collect all results
        summary.output.iterator().each(function(key, value) {
            const results = JSON.parse(value);

            if (key === 'success') {
                successCount += results.length;
                successDetails.push(...results);
            } else if (key === 'failed') {
                failedCount += results.length;
                failedDetails.push(...results);
            }

            return true;
        });

        const totalProcessed = successCount + failedCount;
        const successRate = totalProcessed > 0
            ? ((successCount / totalProcessed) * 100).toFixed(2)
            : 0;

        const finalResults = {
            total_processed: totalProcessed,
            successful: successCount,
            failed: failedCount,
            success_rate: successRate + '%',
            timestamp: new Date().toISOString()
        };

        log.audit('Final Results', finalResults);

        // Log failures in detail
        if (failedCount > 0) {
            log.error('Failed Deactivations', {
                count: failedCount,
                details: failedDetails
            });
        }

        // Log successes
        if (successCount > 0) {
            log.audit('Successful Deactivations', {
                count: successCount,
                sample_details: successDetails.slice(0, 10) // First 10 for reference
            });
        }

        // Check for errors during execution
        summary.mapSummary.errors.iterator().each(function(key, error) {
            log.error('Map Stage Error', {
                key: key,
                error: error
            });
            return true;
        });

        summary.reduceSummary.errors.iterator().each(function(key, error) {
            log.error('Reduce Stage Error', {
                key: key,
                error: error
            });
            return true;
        });

        // Get script parameters for logging
        const script = runtime.getCurrentScript();
        const requestedBy = script.getParameter({
            name: 'custscript_requested_by'
        });
        const reason = script.getParameter({
            name: 'custscript_deactivation_reason'
        });
        const dryRun = script.getParameter({
            name: 'custscript_dry_run'
        });

        log.audit('Execution Summary', {
            requested_by: requestedBy,
            reason: reason,
            dry_run: dryRun === 'T' || dryRun === true,
            ...finalResults
        });
    }

    return {
        getInputData: getInputData,
        map: map,
        reduce: reduce,
        summarize: summarize
    };
});
