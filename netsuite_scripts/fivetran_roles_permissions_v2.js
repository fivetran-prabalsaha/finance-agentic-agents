/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * Fivetran Roles & Permissions Extraction RESTlet v2
 *
 * v2 Changes:
 * - Uses record.load() instead of SuiteQL for permissions
 * - Works with both standard and custom roles
 * - More reliable permission extraction
 *
 * Version: 2.0.0
 * Date: 2026-02-12
 */

define(['N/search', 'N/record', 'N/runtime', 'N/log'], function(search, record, runtime, log) {

    /**
     * POST handler - Fetch all Fivetran roles with permissions
     */
    function post(requestBody) {
        const startTime = new Date().getTime();
        const script = runtime.getCurrentScript();
        const startingGovernance = script.getRemainingUsage();

        try {
            log.audit('Fivetran Roles Extraction v2', 'POST request started');

            // Configuration from body
            const includePermissions = requestBody.includePermissions !== false;
            const includeInactive = requestBody.includeInactive === true;
            const rolePrefix = requestBody.rolePrefix || 'Fivetran -';

            // Step 1: Search for all Fivetran roles
            const roles = searchFivetranRoles(rolePrefix, includeInactive);

            log.audit('Roles Found', `Found ${roles.length} role(s)`);

            // Step 2: Fetch permissions for each role using record.load()
            if (includePermissions && roles.length > 0) {
                for (var i = 0; i < roles.length; i++) {
                    var role = roles[i];
                    try {
                        role.permissions = fetchPermissionsForRole(role.role_id, role.is_custom);
                        role.permission_count = role.permissions.length;

                        // Check governance every 5 roles
                        if (i % 5 === 0) {
                            var remaining = script.getRemainingUsage();
                            if (remaining < 100) {
                                log.warning('Low Governance', `Only ${remaining} units remaining, stopping at role ${i+1}/${roles.length}`);
                                break;
                            }
                        }
                    } catch (e) {
                        log.error('Error fetching permissions for role', `${role.role_name}: ${e.toString()}`);
                        role.permissions = [];
                        role.permission_count = 0;
                        role.error = e.toString();
                    }
                }
            }

            const endTime = new Date().getTime();
            const endingGovernance = script.getRemainingUsage();

            return {
                success: true,
                data: {
                    roles: roles,
                    metadata: {
                        total_roles: roles.length,
                        role_prefix: rolePrefix,
                        include_permissions: includePermissions,
                        include_inactive: includeInactive,
                        execution_time_ms: endTime - startTime,
                        governance_used: startingGovernance - endingGovernance,
                        governance_remaining: endingGovernance
                    }
                }
            };

        } catch (e) {
            log.error('POST Error', e.toString());
            return {
                success: false,
                error: e.toString(),
                message: 'Error fetching Fivetran roles and permissions'
            };
        }
    }

    /**
     * GET handler - Same as POST
     */
    function get(requestParams) {
        return post({
            includePermissions: requestParams.includePermissions !== 'false',
            includeInactive: requestParams.includeInactive === 'true',
            rolePrefix: requestParams.rolePrefix || 'Fivetran -'
        });
    }

    /**
     * Search for all roles starting with specified prefix
     */
    function searchFivetranRoles(rolePrefix, includeInactive) {
        const roles = [];

        try {
            const filters = [
                ['name', 'startswith', rolePrefix]
            ];

            if (!includeInactive) {
                filters.push('AND');
                filters.push(['isinactive', 'is', 'F']);
            }

            const roleSearch = search.create({
                type: search.Type.ROLE,
                filters: filters,
                columns: [
                    search.createColumn({ name: 'internalid' }),
                    search.createColumn({ name: 'name' }),
                    search.createColumn({ name: 'isinactive' })
                ]
            });

            roleSearch.run().each(function(result) {
                const roleId = result.getValue('internalid');
                const roleName = result.getValue('name');
                const isInactive = result.getValue('isinactive') === 'T';

                roles.push({
                    role_id: roleId,
                    role_name: roleName,
                    is_inactive: isInactive,
                    is_custom: roleId.toString().indexOf('customrole') === 0,
                    permissions: [],
                    permission_count: 0
                });

                return true;
            });

            log.audit('Role Search Complete', `Found ${roles.length} roles`);
            return roles;

        } catch (e) {
            log.error('Error searching roles', e.toString());
            throw e;
        }
    }

    /**
     * Fetch permissions for a single role using record.load()
     *
     * This method loads the role record and extracts permissions from it.
     * Works for both standard and custom roles.
     */
    function fetchPermissionsForRole(roleId, isCustom) {
        const permissions = [];

        try {
            log.debug('Fetching permissions', `Role ID: ${roleId}, Custom: ${isCustom}`);

            // Load the role record
            var roleRecord = record.load({
                type: record.Type.ROLE,
                id: roleId,
                isDynamic: false
            });

            // Get the number of permission lines
            var lineCount = roleRecord.getLineCount({
                sublistId: 'permissions'
            });

            log.debug('Permission Lines', `Found ${lineCount} permission lines for role ${roleId}`);

            // Extract each permission
            for (var i = 0; i < lineCount; i++) {
                try {
                    var permId = roleRecord.getSublistValue({
                        sublistId: 'permissions',
                        fieldId: 'permkey',
                        line: i
                    });

                    var permLevel = roleRecord.getSublistValue({
                        sublistId: 'permissions',
                        fieldId: 'permlevel',
                        line: i
                    });

                    var permName = roleRecord.getSublistText({
                        sublistId: 'permissions',
                        fieldId: 'permkey',
                        line: i
                    }) || permId;

                    if (permId) {
                        permissions.push({
                            permission_id: permId.toString(),
                            permission_name: permName,
                            permission_level: permLevel ? permLevel.toString() : '0'
                        });
                    }
                } catch (lineError) {
                    log.error('Error reading permission line', `Line ${i}: ${lineError.toString()}`);
                }
            }

            log.debug('Permissions Extracted', `Role ${roleId}: ${permissions.length} permissions`);
            return permissions;

        } catch (e) {
            log.error('Error loading role record', `Role ${roleId}: ${e.toString()}`);
            return [];
        }
    }

    return {
        get: get,
        post: post
    };
});
