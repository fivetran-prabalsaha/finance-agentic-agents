/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * NetSuite RESTlet for User Search with Roles and Permissions (v5 - HYBRID)
 *
 * Purpose: Search for specific users and return their roles and permissions
 *
 * v5 STRATEGY:
 * - Uses ORIGINAL saved search method for roles (PROVEN TO WORK!)
 * - Adds SuiteQL for permissions (RolePermissions table)
 * - Best of both worlds: proven role fetching + efficient permission fetching
 *
 * Version: 5.0.0 (Hybrid: Saved Search + SuiteQL)
 * Date: 2026-02-11
 */

define(['N/search', 'N/query', 'N/runtime', 'N/log'], function(search, query, runtime, log) {

    /**
     * POST handler - Search for users with roles and permissions
     */
    function post(requestBody) {
        const startTime = new Date().getTime();
        const script = runtime.getCurrentScript();
        const startingGovernance = script.getRemainingUsage();

        try {
            log.audit('User Search Request (v5.0)', JSON.stringify(requestBody));

            const searchValue = requestBody.searchValue;
            const searchType = requestBody.searchType || 'both';
            const includePermissions = requestBody.includePermissions !== false;
            const includeInactive = requestBody.includeInactive === true;

            if (!searchValue) {
                return {
                    success: false,
                    error: 'searchValue is required',
                    message: 'Please provide a name or email to search for'
                };
            }

            // Step 1: Search for users
            const users = searchUsers(searchValue, searchType, includeInactive);

            log.audit('Search Results', `Found ${users.length} user(s)`);

            if (users.length === 0) {
                return {
                    success: true,
                    data: {
                        users: [],
                        metadata: {
                            search_value: searchValue,
                            users_found: 0
                        }
                    }
                };
            }

            // Step 2: Fetch roles using ORIGINAL proven method
            const enrichedUsers = users.map(user => enrichUserWithRoles(user));

            // Step 3: Batch fetch permissions if requested
            if (includePermissions) {
                // Collect all unique role IDs
                const allRoleIds = [];
                enrichedUsers.forEach(user => {
                    user.roles.forEach(role => {
                        if (allRoleIds.indexOf(role.role_id) === -1) {
                            allRoleIds.push(role.role_id);
                        }
                    });
                });

                if (allRoleIds.length > 0) {
                    const permissionsMap = fetchPermissionsForRoles(allRoleIds);

                    // Attach permissions to roles
                    enrichedUsers.forEach(user => {
                        user.roles.forEach(role => {
                            role.permissions = permissionsMap[role.role_id] || [];
                            role.permission_count = role.permissions.length;
                        });
                    });
                }
            }

            const endTime = new Date().getTime();
            const endingGovernance = script.getRemainingUsage();

            return {
                success: true,
                data: {
                    users: enrichedUsers,
                    metadata: {
                        search_value: searchValue,
                        search_type: searchType,
                        users_found: enrichedUsers.length,
                        execution_time_seconds: (endTime - startTime) / 1000,
                        timestamp: new Date().toISOString(),
                        version: '5.0.0-hybrid'
                    }
                },
                governance: {
                    starting_units: startingGovernance,
                    ending_units: endingGovernance,
                    units_used: startingGovernance - endingGovernance,
                    units_per_user: enrichedUsers.length > 0 ?
                        ((startingGovernance - endingGovernance) / enrichedUsers.length).toFixed(2) : 0
                }
            };

        } catch (e) {
            log.error('User Search Error', e.toString());
            return {
                success: false,
                error: e.toString(),
                message: 'Failed to search for users'
            };
        }
    }

    /**
     * Derive job function from department, title, and business unit
     * This helps classify users for context-aware SOD analysis
     */
    function deriveJobFunction(department, title, businessUnit) {
        const deptLower = (department || '').toLowerCase();
        const titleLower = (title || '').toLowerCase();
        const buLower = (businessUnit || '').toLowerCase();

        // Check for IT/Systems Engineering
        if (deptLower.includes('systems engineering') ||
            deptLower.includes('system engineering') ||
            deptLower.includes('it') ||
            deptLower.includes('technology') ||
            deptLower.includes('engineering') ||
            titleLower.includes('engineer') ||
            titleLower.includes('systems') ||
            titleLower.includes('devops') ||
            titleLower.includes('sre')) {
            return 'IT/SYSTEMS_ENGINEERING';
        }

        // Check for Finance
        if (deptLower.includes('finance') ||
            deptLower.includes('controller') ||
            titleLower.includes('finance') ||
            titleLower.includes('controller') ||
            titleLower.includes('cfo')) {
            return 'FINANCE';
        }

        // Check for Accounting
        if (deptLower.includes('accounting') ||
            titleLower.includes('accountant') ||
            titleLower.includes('accounting')) {
            return 'ACCOUNTING';
        }

        // Check for AP/AR
        if (deptLower.includes('accounts payable') ||
            deptLower.includes('ap ') ||
            titleLower.includes('ap ') ||
            titleLower.includes('accounts payable')) {
            return 'ACCOUNTS_PAYABLE';
        }

        if (deptLower.includes('accounts receivable') ||
            deptLower.includes('ar ') ||
            titleLower.includes('ar ') ||
            titleLower.includes('accounts receivable')) {
            return 'ACCOUNTS_RECEIVABLE';
        }

        // Check for Sales
        if (deptLower.includes('sales') ||
            titleLower.includes('sales') ||
            titleLower.includes('account executive')) {
            return 'SALES';
        }

        // Check for Procurement
        if (deptLower.includes('procurement') ||
            deptLower.includes('purchasing') ||
            titleLower.includes('buyer') ||
            titleLower.includes('procurement')) {
            return 'PROCUREMENT';
        }

        // Check for HR
        if (deptLower.includes('human resources') ||
            deptLower.includes(' hr') ||
            titleLower.includes('hr ') ||
            titleLower.includes('human resources')) {
            return 'HUMAN_RESOURCES';
        }

        // Check for Executive
        if (titleLower.includes('ceo') ||
            titleLower.includes('cfo') ||
            titleLower.includes('coo') ||
            titleLower.includes('cto') ||
            titleLower.includes('chief') ||
            titleLower.includes('president')) {
            return 'EXECUTIVE';
        }

        // Check for G&A (General & Administrative)
        if (deptLower.includes('g&a') ||
            deptLower.includes('general') ||
            deptLower.includes('administrative')) {
            return 'GENERAL_ADMIN';
        }

        return 'OTHER';
    }

    /**
     * Search for users using saved search
     */
    function searchUsers(searchValue, searchType, includeInactive) {
        const users = [];
        let filters = [];

        try {
            if (!includeInactive) {
                filters.push(['isinactive', 'is', 'F']);
            }

            if (filters.length > 0) {
                filters.push('AND');
            }

            if (searchType === 'name') {
                filters.push(['entityid', 'contains', searchValue]);
            } else if (searchType === 'email') {
                filters.push(['email', 'contains', searchValue]);
            } else {
                filters.push([
                    ['entityid', 'contains', searchValue],
                    'OR',
                    ['email', 'contains', searchValue]
                ]);
            }

            const userSearch = search.create({
                type: search.Type.EMPLOYEE,
                filters: filters,
                columns: [
                    search.createColumn({ name: 'internalid' }),
                    search.createColumn({ name: 'entityid' }),
                    search.createColumn({ name: 'email' }),
                    search.createColumn({ name: 'firstname' }),
                    search.createColumn({ name: 'lastname' }),
                    search.createColumn({ name: 'title' }),
                    search.createColumn({ name: 'department' }),
                    search.createColumn({ name: 'subsidiary' }),
                    search.createColumn({ name: 'isinactive' }),
                    // NEW: Context fields for SOD analysis
                    search.createColumn({ name: 'class' }),        // Business Unit/Cost Center
                    search.createColumn({ name: 'supervisor' }),   // Manager
                    search.createColumn({ name: 'location' }),     // Office location
                    search.createColumn({ name: 'hiredate' })      // Hire date
                ]
            });

            userSearch.run().each(function(result) {
                const department = result.getText('department') || '';
                const title = result.getText('title') || '';
                const classField = result.getText('class') || '';

                // Derive job function from department, title, and class
                const jobFunction = deriveJobFunction(department, title, classField);

                users.push({
                    user_id: result.getValue('entityid'),
                    email: result.getValue('email'),
                    first_name: result.getValue('firstname'),
                    last_name: result.getValue('lastname'),
                    name: `${result.getValue('firstname')} ${result.getValue('lastname')}`.trim(),
                    title: title,
                    department: department,
                    subsidiary: result.getText('subsidiary') || null,
                    is_active: result.getValue('isinactive') === 'F',
                    internal_id: result.id,

                    // NEW: Context fields for SOD analysis
                    business_unit: classField,
                    cost_center: classField,  // Often same as class in NetSuite
                    supervisor: result.getText('supervisor') || null,
                    supervisor_id: result.getValue('supervisor') || null,
                    location: result.getText('location') || null,
                    hire_date: result.getValue('hiredate') || null,
                    job_function: jobFunction  // Derived field
                });
                return true;
            });

        } catch (e) {
            log.error('Error searching users', e.toString());
        }

        return users;
    }

    /**
     * Enrich user with roles using ORIGINAL proven method
     * This is the same method that was working in the original script
     */
    function enrichUserWithRoles(user) {
        try {
            log.audit('Fetching roles for user', `${user.name} (${user.internal_id})`);

            // ORIGINAL METHOD - Saved search with 'role' field
            const roleSearch = search.create({
                type: search.Type.EMPLOYEE,
                filters: [
                    ['internalid', 'anyof', user.internal_id]
                ],
                columns: [
                    search.createColumn({
                        name: 'role',
                        summary: search.Summary.GROUP
                    })
                ]
            });

            const roles = [];

            roleSearch.run().each(function(result) {
                const roleId = result.getValue({
                    name: 'role',
                    summary: search.Summary.GROUP
                });

                const roleName = result.getText({
                    name: 'role',
                    summary: search.Summary.GROUP
                });

                // FILTER: Only include roles that start with "Fivetran -"
                if (roleId && roleName && roleName.indexOf('Fivetran -') === 0) {
                    roles.push({
                        role_id: roleId,
                        role_name: roleName,
                        permissions: [] // Will be filled later
                    });
                }

                return true;
            });

            log.audit('Roles found', `User ${user.name}: ${roles.length} roles`);

            user.roles = roles;
            user.roles_count = roles.length;

            return user;

        } catch (e) {
            log.error('Error enriching user with roles', `User: ${user.email}, Error: ${e.toString()}`);
            user.roles = [];
            user.roles_count = 0;
            return user;
        }
    }

    /**
     * Fetch permissions for roles using SuiteQL (efficient batch query)
     */
    function fetchPermissionsForRoles(roleIds) {
        try {
            if (!roleIds || roleIds.length === 0) {
                return {};
            }

            // Validate and sanitize role IDs
            const sanitizedIds = roleIds
                .map(id => {
                    const str = id.toString();
                    if (str.indexOf('customrole') === 0) {
                        return "'" + str + "'";
                    }
                    const num = parseInt(id);
                    return !isNaN(num) && num > 0 ? num : null;
                })
                .filter(id => id !== null);

            if (sanitizedIds.length === 0) {
                log.audit('No valid role IDs', 'Skipping permission fetch');
                return {};
            }

            log.audit('Fetching Permissions', `For ${sanitizedIds.length} role(s)`);

            const sql = `
                SELECT
                    role AS role_id,
                    permkey AS key,
                    name AS permission_name,
                    BUILTIN.DF(permlevel) AS level
                FROM RolePermissions
                WHERE role IN (${sanitizedIds.join(',')})
                ORDER BY role, name`;

            const results = query.runSuiteQL({ query: sql }).asMappedResults();

            log.audit('Permissions Fetched', `${results.length} permissions found`);

            const permissionsMap = {};
            results.forEach(res => {
                const roleId = res.role_id.toString();

                if (!permissionsMap[roleId]) {
                    permissionsMap[roleId] = [];
                }

                permissionsMap[roleId].push({
                    key: res.key,
                    permission: res.key,
                    permission_name: res.permission_name,
                    level: res.level
                });
            });

            return permissionsMap;

        } catch (e) {
            log.error('Error fetching permissions', e.toString());
            return {};
        }
    }

    /**
     * GET handler for testing
     */
    function get(requestParams) {
        return {
            success: true,
            message: 'User Search RESTlet v5.0 (HYBRID - Proven + Enhanced) is active',
            version: '5.0.0-hybrid',
            usage: {
                method: 'POST',
                example_request: {
                    searchType: 'email',
                    searchValue: 'john.doe@company.com',
                    includePermissions: true,
                    includeInactive: false
                }
            },
            approach: [
                'v5.0: Uses ORIGINAL saved search for roles (proven to work)',
                'v5.0: Adds SuiteQL for permissions (efficient batch query)',
                'v5.0: Best of both worlds - reliability + efficiency',
                'v5.0: If original got role names, this will too + permissions!'
            ]
        };
    }

    return {
        post: post,
        get: get
    };

});
