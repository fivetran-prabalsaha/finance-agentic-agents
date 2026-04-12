/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * Fivetran Roles & Permissions - SuiteQL Approach
 *
 * This version uses SuiteQL with JOINs instead of record.load()
 * to extract permissions from standard NetSuite roles.
 *
 * WHY THIS APPROACH:
 * - record.load() does NOT work for standard NetSuite roles
 * - All 28 Fivetran roles are standard roles (not custom)
 * - SuiteQL can query the rolepermissions table directly
 * - This bypasses the record.load() limitation
 *
 * Version: 3.0.0 (SuiteQL)
 * Date: 2026-02-12
 */

define(['N/query', 'N/log', 'N/runtime'], (query, log, runtime) => {

    /**
     * GET handler - Fetch all Fivetran roles with permissions using SuiteQL
     */
    const doGet = (requestParams) => {
        const startTime = Date.now();
        const script = runtime.getCurrentScript();
        const startingGovernance = script.getRemainingUsage();

        try {
            log.audit('Fivetran Roles SuiteQL', 'GET request started');

            // Configuration from query params
            const rolePrefix = requestParams.rolePrefix || 'Fivetran';
            const includeInactive = requestParams.includeInactive === 'true';

            // Build SuiteQL query
            let suiteQL = `
                SELECT
                    r.id AS roleid,
                    r.name AS rolename,
                    r.isinactive AS isinactive,
                    rp.permkey AS permissionid,
                    BUILTIN.DF(rp.permkey) AS permissionname,
                    rp.permlevel AS levelid,
                    BUILTIN.DF(rp.permlevel) AS levelname
                FROM
                    role r
                LEFT JOIN
                    rolepermissions rp ON r.id = rp.role
                WHERE
                    r.name LIKE '${rolePrefix}%'
            `;

            if (!includeInactive) {
                suiteQL += ` AND r.isinactive = 'F'`;
            }

            suiteQL += `
                ORDER BY
                    r.name, rp.permkey
            `;

            log.debug('SuiteQL Query', suiteQL);

            // Execute query
            const resultSet = query.runSuiteQL({ query: suiteQL });
            const results = resultSet.asMappedResults();

            log.audit('Query Results', `Retrieved ${results.length} rows`);

            // Group flat results by Role
            const groupedRoles = results.reduce((acc, row) => {
                const roleId = row.roleid;

                if (!acc[roleId]) {
                    acc[roleId] = {
                        role_id: roleId,
                        role_name: row.rolename,
                        is_inactive: row.isinactive === 'T',
                        is_custom: roleId.toString().startsWith('customrole'),
                        permissions: [],
                        permission_count: 0
                    };
                }

                // Add permission if it exists (LEFT JOIN may have nulls)
                if (row.permissionid) {
                    acc[roleId].permissions.push({
                        permission_id: row.permissionid,
                        permission_name: row.permissionname || row.permissionid,
                        permission_level: row.levelname || 'None',
                        permission_level_value: row.levelid
                    });
                    acc[roleId].permission_count++;
                }

                return acc;
            }, {});

            const rolesArray = Object.values(groupedRoles);

            const endTime = Date.now();
            const endingGovernance = script.getRemainingUsage();

            const response = {
                success: true,
                data: {
                    roles: rolesArray,
                    metadata: {
                        total_roles: rolesArray.length,
                        roles_with_permissions: rolesArray.filter(r => r.permission_count > 0).length,
                        total_permissions: rolesArray.reduce((sum, r) => sum + r.permission_count, 0),
                        role_prefix: rolePrefix,
                        include_inactive: includeInactive,
                        execution_time_ms: endTime - startTime,
                        governance_used: startingGovernance - endingGovernance,
                        governance_remaining: endingGovernance,
                        timestamp: new Date().toISOString(),
                        method: 'SuiteQL JOIN'
                    }
                }
            };

            log.audit('Processing Complete', JSON.stringify(response.data.metadata));

            return response;

        } catch (e) {
            log.error('GET Error', e.toString());
            log.error('Error Stack', e.stack);
            return {
                success: false,
                error: e.message || e.toString(),
                stack: e.stack
            };
        }
    };

    /**
     * POST handler - Same as GET but accepts body params
     */
    const doPost = (requestBody) => {
        log.audit('POST Request', JSON.stringify(requestBody));

        // Convert POST body to GET-style params
        return doGet({
            rolePrefix: requestBody.rolePrefix || 'Fivetran',
            includeInactive: requestBody.includeInactive ? 'true' : 'false'
        });
    };

    return {
        get: doGet,
        post: doPost
    };
});
