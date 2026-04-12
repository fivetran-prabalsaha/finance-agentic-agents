/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * NetSuite User Deactivation RESTlet
 *
 * Handles single user or small batch deactivation (max 10 users)
 * For bulk operations (>10 users), use Map/Reduce script
 */

define(['N/record', 'N/error'], function(record, error) {

    /**
     * POST handler - Deactivate user(s)
     *
     * Request body:
     * {
     *   "user_ids": ["123", "456", "789"],
     *   "dry_run": false,
     *   "reason": "Terminated in Okta",
     *   "requested_by": "admin@company.com"
     * }
     *
     * Response:
     * {
     *   "success": true,
     *   "dry_run": false,
     *   "total": 3,
     *   "deactivated": 2,
     *   "failed": 1,
     *   "errors": [...]
     * }
     */
    function post(requestBody) {
        log.audit('Deactivation Request', JSON.stringify(requestBody));

        const userIds = requestBody.user_ids || [];
        const dryRun = requestBody.dry_run || false;
        const reason = requestBody.reason || 'Okta reconciliation';
        const requestedBy = requestBody.requested_by || 'system';

        // Validate input
        if (!userIds || userIds.length === 0) {
            throw error.create({
                name: 'MISSING_REQUIRED_PARAMETER',
                message: 'user_ids array is required'
            });
        }

        if (userIds.length > 10) {
            throw error.create({
                name: 'TOO_MANY_USERS',
                message: 'Use Map/Reduce script for more than 10 users (provided ' + userIds.length + ')'
            });
        }

        const results = {
            success: true,
            dry_run: dryRun,
            total: userIds.length,
            deactivated: 0,
            failed: 0,
            errors: [],
            details: []
        };

        // Process each user
        for (let i = 0; i < userIds.length; i++) {
            const userId = userIds[i];

            try {
                if (!dryRun) {
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
                        log.audit('Already Inactive', `User ID: ${userId}, Name: ${name}`);
                        results.details.push({
                            user_id: userId,
                            email: email,
                            name: name,
                            status: 'already_inactive',
                            message: 'User was already inactive'
                        });
                        results.deactivated++;
                        continue;
                    }

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
                        log.debug('Comment Update Failed', commentError.message);
                        // Don't fail the entire operation if comment update fails
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

                    results.details.push({
                        user_id: userId,
                        email: email,
                        name: name,
                        status: 'deactivated',
                        message: 'Successfully deactivated'
                    });

                    results.deactivated++;
                } else {
                    // Dry run - just check if user exists
                    const employeeRecord = record.load({
                        type: record.Type.EMPLOYEE,
                        id: userId
                    });

                    const email = employeeRecord.getValue({ fieldId: 'email' });
                    const name = employeeRecord.getValue({ fieldId: 'entityid' });
                    const currentStatus = employeeRecord.getValue({ fieldId: 'isinactive' });

                    log.audit('Dry Run', `Would deactivate user: ${userId} (${name})`);

                    results.details.push({
                        user_id: userId,
                        email: email,
                        name: name,
                        current_status: currentStatus ? 'inactive' : 'active',
                        status: 'dry_run',
                        message: 'Dry run - no changes made'
                    });

                    results.deactivated++;
                }

            } catch (e) {
                log.error('Deactivation Failed', {
                    user_id: userId,
                    error: e.message,
                    error_name: e.name
                });

                results.failed++;
                results.errors.push({
                    user_id: userId,
                    error: e.message,
                    error_code: e.name
                });
            }
        }

        // Update overall success flag
        results.success = results.failed === 0;

        log.audit('Deactivation Complete', {
            total: results.total,
            deactivated: results.deactivated,
            failed: results.failed,
            success_rate: ((results.deactivated / results.total) * 100).toFixed(2) + '%'
        });

        return results;
    }

    /**
     * GET handler - Get user status
     *
     * Query params: user_ids=123,456,789
     */
    function get(requestParams) {
        const userIdsParam = requestParams.user_ids || '';
        const userIds = userIdsParam.split(',').map(id => id.trim()).filter(id => id);

        if (userIds.length === 0) {
            throw error.create({
                name: 'MISSING_REQUIRED_PARAMETER',
                message: 'user_ids parameter is required (comma-separated)'
            });
        }

        const results = {
            success: true,
            total: userIds.length,
            users: [],
            errors: []
        };

        for (let i = 0; i < userIds.length; i++) {
            const userId = userIds[i];

            try {
                const employeeRecord = record.load({
                    type: record.Type.EMPLOYEE,
                    id: userId
                });

                results.users.push({
                    user_id: userId,
                    internal_id: employeeRecord.id,
                    name: employeeRecord.getValue({ fieldId: 'entityid' }),
                    email: employeeRecord.getValue({ fieldId: 'email' }),
                    is_inactive: employeeRecord.getValue({ fieldId: 'isinactive' }),
                    department: employeeRecord.getText({ fieldId: 'department' }),
                    supervisor: employeeRecord.getText({ fieldId: 'supervisor' })
                });

            } catch (e) {
                log.error('Get User Failed', {
                    user_id: userId,
                    error: e.message
                });

                results.errors.push({
                    user_id: userId,
                    error: e.message
                });
            }
        }

        return results;
    }

    return {
        post: post,
        get: get
    };
});
