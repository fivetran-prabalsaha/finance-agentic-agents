/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * Fivetran Roles & Permissions Extraction RESTlet
 *
 * Purpose: Extract all Fivetran roles and their complete permission sets
 * for SOD (Segregation of Duties) analysis and rule creation
 *
 * This RESTlet is ROLE-CENTRIC (not user-centric):
 * - Fetches all roles starting with "Fivetran -"
 * - Gets complete permission list for each role
 * - Returns role data without user assignments
 * - Fast and efficient for permission conflict analysis
 *
 * Endpoints:
 *   GET  - Fetch all Fivetran roles with permissions
 *   POST - Same as GET (supports both methods)
 *
 * Usage:
 *   GET https://[account].restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=XXX&deploy=1
 *
 * Version: 1.0.0
 * Date: 2026-02-12
 * Author: Prabal Saha
 */

define(['N/search', 'N/query', 'N/runtime', 'N/log'], function(search, query, runtime, log) {

    /**
     * GET handler - Fetch all Fivetran roles with permissions
     */
    function get(requestParams) {
        const startTime = new Date().getTime();
        const script = runtime.getCurrentScript();
        const startingGovernance = script.getRemainingUsage();

        try {
            log.audit('Fivetran Roles Extraction', 'GET request started');

            // Configuration
            const includePermissions = requestParams.includePermissions !== 'false';
            const includeInactive = requestParams.includeInactive === 'true';
            const rolePrefix = requestParams.rolePrefix || 'Fivetran -';

            // Step 1: Search for all Fivetran roles
            const roles = searchFivetranRoles(rolePrefix, includeInactive);

            log.audit('Roles Found', `Found ${roles.length} role(s) starting with "${rolePrefix}"`);

            // Step 2: Fetch permissions for each role
            if (includePermissions && roles.length > 0) {
                const roleIds = roles.map(function(role) { return role.role_id; });
                const permissionsMap = fetchPermissionsForRoles(roleIds);

                // Attach permissions to roles
                roles.forEach(function(role) {
                    role.permissions = permissionsMap[role.role_id] || [];
                    role.permission_count = role.permissions.length;
                });
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
                        governance_used: startingGovernance - endingGovernance
                    }
                }
            };

        } catch (e) {
            log.error('GET Error', e.toString());
            return {
                success: false,
                error: e.toString(),
                message: 'Error fetching Fivetran roles and permissions'
            };
        }
    }

    /**
     * POST handler - Same as GET (for consistency with other RESTlets)
     */
    function post(requestBody) {
        const startTime = new Date().getTime();
        const script = runtime.getCurrentScript();
        const startingGovernance = script.getRemainingUsage();

        try {
            log.audit('Fivetran Roles Extraction', 'POST request started');

            // Configuration from body
            const includePermissions = requestBody.includePermissions !== false;
            const includeInactive = requestBody.includeInactive === true;
            const rolePrefix = requestBody.rolePrefix || 'Fivetran -';

            // Step 1: Search for all Fivetran roles
            const roles = searchFivetranRoles(rolePrefix, includeInactive);

            log.audit('Roles Found', `Found ${roles.length} role(s) starting with "${rolePrefix}"`);

            // Step 2: Fetch permissions for each role
            if (includePermissions && roles.length > 0) {
                const roleIds = roles.map(function(role) { return role.role_id; });
                const permissionsMap = fetchPermissionsForRoles(roleIds);

                // Attach permissions to roles
                roles.forEach(function(role) {
                    role.permissions = permissionsMap[role.role_id] || [];
                    role.permission_count = role.permissions.length;
                });
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
                        governance_used: startingGovernance - endingGovernance
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
     * Search for all roles starting with specified prefix
     *
     * @param {string} rolePrefix - Role name prefix (default: "Fivetran -")
     * @param {boolean} includeInactive - Include inactive roles
     * @returns {Array} Array of role objects
     */
    function searchFivetranRoles(rolePrefix, includeInactive) {
        const roles = [];

        try {
            // Build filters
            const filters = [
                ['name', 'startswith', rolePrefix]
            ];

            if (!includeInactive) {
                filters.push('AND');
                filters.push(['isinactive', 'is', 'F']);
            }

            // Create search
            const roleSearch = search.create({
                type: search.Type.ROLE,
                filters: filters,
                columns: [
                    search.createColumn({ name: 'internalid' }),
                    search.createColumn({ name: 'name' }),
                    search.createColumn({ name: 'isinactive' })
                ]
            });

            // Execute search
            roleSearch.run().each(function(result) {
                const roleId = result.getValue('internalid');
                const roleName = result.getValue('name');
                const isInactive = result.getValue('isinactive') === 'T';

                roles.push({
                    role_id: roleId,
                    role_name: roleName,
                    is_inactive: isInactive,
                    is_custom: roleId.indexOf('customrole') === 0,
                    permissions: [], // Will be filled later if requested
                    permission_count: 0
                });

                return true; // Continue iteration
            });

            log.audit('Role Search Complete', `Found ${roles.length} roles`);
            return roles;

        } catch (e) {
            log.error('Error searching roles', e.toString());
            throw e;
        }
    }

    /**
     * Fetch permissions for multiple roles using SuiteQL (batch query)
     *
     * @param {Array} roleIds - Array of role internal IDs
     * @returns {Object} Map of roleId -> permissions array
     */
    function fetchPermissionsForRoles(roleIds) {
        const permissionsMap = {};

        try {
            if (roleIds.length === 0) {
                return permissionsMap;
            }

            log.audit('Fetching Permissions', `Querying permissions for ${roleIds.length} roles`);

            // Build roleIds list for SQL IN clause
            const roleIdsList = roleIds.map(function(id) { return "'" + id + "'"; }).join(',');

            // SuiteQL query to fetch permissions for all roles at once
            const sql = `
                SELECT
                    rp.role AS role_id,
                    rp.permission AS permission_id,
                    p.name AS permission_name,
                    rp.level AS permission_level
                FROM
                    RolePermissions rp
                LEFT JOIN
                    Permission p ON rp.permission = p.id
                WHERE
                    rp.role IN (${roleIdsList})
                ORDER BY
                    rp.role, p.name
            `;

            log.debug('SuiteQL Query', sql);

            // Execute query
            const resultSet = query.runSuiteQL({ query: sql });
            const results = resultSet.asMappedResults();

            log.audit('Permissions Query Complete', `Retrieved ${results.length} permission records`);

            // Process results into map
            results.forEach(function(row) {
                const roleId = row.role_id;
                const permissionName = row.permission_name;
                const permissionLevel = row.permission_level;

                // Initialize array if first permission for this role
                if (!permissionsMap[roleId]) {
                    permissionsMap[roleId] = [];
                }

                // Add permission with level
                permissionsMap[roleId].push({
                    permission_id: row.permission_id,
                    permission_name: permissionName,
                    permission_level: permissionLevel
                });
            });

            log.audit('Permissions Mapped', `Mapped permissions for ${Object.keys(permissionsMap).length} roles`);
            return permissionsMap;

        } catch (e) {
            log.error('Error fetching permissions', e.toString());
            // Return empty map on error (don't fail entire request)
            return permissionsMap;
        }
    }

    // Export functions
    return {
        get: get,
        post: post
    };
});
