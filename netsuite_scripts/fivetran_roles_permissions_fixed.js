/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 *
 * Fivetran Roles & Permissions - FIXED VERSION
 * Issue: record.Type.ROLE doesn't exist
 * Solution: Use 'role' string directly
 */
define(['N/record', 'N/search', 'N/log', 'N/runtime'], (record, search, log, runtime) => {

    const fetchRolesWithPermissions = (rolePrefix = 'Fivetran -', includeInactive = false) => {
        const script = runtime.getCurrentScript();
        const startingGovernance = script.getRemainingUsage();
        const startTime = Date.now();

        let roleData = [];

        try {
            // Build filters
            const filters = [['name', 'startswith', rolePrefix]];

            if (!includeInactive) {
                filters.push('AND');
                filters.push(['isinactive', 'is', 'F']);
            }

            // Search for roles
            const roleSearch = search.create({
                type: search.Type.ROLE,
                filters: filters,
                columns: ['name', 'internalid', 'isinactive']
            });

            roleSearch.run().each((result) => {
                const roleId = result.id;
                const roleName = result.getValue('name');
                const isInactive = result.getValue('isinactive') === 'T';

                try {
                    // Load role record using string 'role' instead of record.Type.ROLE
                    const roleRecord = record.load({
                        type: 'role',  // ← FIXED: Use string instead of record.Type.ROLE
                        id: roleId,
                        isDynamic: false
                    });

                    // Extract permissions
                    let permissions = [];
                    const lineCount = roleRecord.getLineCount({ sublistId: 'permissions' });

                    log.debug('Permission Lines', `Role ${roleId} (${roleName}): ${lineCount} lines`);

                    for (let i = 0; i < lineCount; i++) {
                        try {
                            const permId = roleRecord.getSublistValue({
                                sublistId: 'permissions',
                                fieldId: 'permkey',
                                line: i
                            });

                            const permName = roleRecord.getSublistText({
                                sublistId: 'permissions',
                                fieldId: 'permkey',
                                line: i
                            });

                            const permLevel = roleRecord.getSublistValue({
                                sublistId: 'permissions',
                                fieldId: 'permlevel',
                                line: i
                            });

                            if (permId) {
                                permissions.push({
                                    permission_id: permId,
                                    permission_name: permName || permId,
                                    permission_level: permLevel ? permLevel.toString() : '0'
                                });
                            }
                        } catch (lineError) {
                            log.error('Permission Line Error', `Role ${roleId}, Line ${i}: ${lineError.toString()}`);
                        }
                    }

                    roleData.push({
                        role_id: roleId,
                        role_name: roleName,
                        is_inactive: isInactive,
                        is_custom: roleId.toString().indexOf('customrole') === 0,
                        permissions: permissions,
                        permission_count: permissions.length
                    });

                    log.audit('Role Processed', `${roleName}: ${permissions.length} permissions`);

                } catch (roleError) {
                    log.error('Error loading role', `${roleName} (${roleId}): ${roleError.toString()}`);

                    roleData.push({
                        role_id: roleId,
                        role_name: roleName,
                        is_inactive: isInactive,
                        is_custom: roleId.toString().indexOf('customrole') === 0,
                        permissions: [],
                        permission_count: 0,
                        error: roleError.message || roleError.toString()
                    });
                }

                // Governance check every 5 roles
                if (roleData.length % 5 === 0) {
                    const remaining = script.getRemainingUsage();
                    log.debug('Governance Check', `Processed ${roleData.length} roles, ${remaining} units remaining`);

                    if (remaining < 100) {
                        log.warning('Low Governance', `Stopping at ${roleData.length} roles to prevent timeout`);
                        return false; // Stop iteration
                    }
                }

                return true; // Continue
            });

            const endingGovernance = script.getRemainingUsage();
            const endTime = Date.now();

            log.audit('Processing Complete', `Processed ${roleData.length} roles`);

            return {
                success: true,
                data: {
                    roles: roleData,
                    metadata: {
                        total_roles: roleData.length,
                        roles_with_permissions: roleData.filter(r => r.permission_count > 0).length,
                        role_prefix: rolePrefix,
                        include_inactive: includeInactive,
                        execution_time_ms: endTime - startTime,
                        governance_used: startingGovernance - endingGovernance,
                        governance_remaining: endingGovernance,
                        timestamp: new Date().toISOString()
                    }
                }
            };

        } catch (e) {
            log.error('Fatal Error', e.toString());
            return {
                success: false,
                error: e.message || e.toString(),
                stack: e.stack
            };
        }
    };

    const doGet = (requestParams) => {
        log.audit('GET Request', JSON.stringify(requestParams));
        const rolePrefix = requestParams.rolePrefix || 'Fivetran -';
        const includeInactive = requestParams.includeInactive === 'true';
        return fetchRolesWithPermissions(rolePrefix, includeInactive);
    };

    const doPost = (requestBody) => {
        log.audit('POST Request', JSON.stringify(requestBody));
        const rolePrefix = requestBody.rolePrefix || 'Fivetran -';
        const includeInactive = requestBody.includeInactive === true;
        return fetchRolesWithPermissions(rolePrefix, includeInactive);
    };

    return {
        get: doGet,
        post: doPost
    };
});
