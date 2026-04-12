# NetSuite Permission Analysis & Categorization

**Total Permissions**: 341

## Permissions by Category

- **transaction_entry**: 93 permissions
- **uncategorized**: 74 permissions
- **system_admin**: 69 permissions
- **setup_lists**: 56 permissions
- **financial_reporting**: 46 permissions
- **customer_setup**: 23 permissions
- **bank_reconciliation**: 13 permissions
- **user_admin**: 12 permissions
- **transaction_approval**: 10 permissions
- **transaction_payment**: 9 permissions
- **vendor_setup**: 5 permissions
- **role_admin**: 2 permissions

## Permissions by Risk Level

- **HIGH**: 7 permissions
- **MEDIUM**: 13 permissions
- **LOW**: 131 permissions
- **MINIMAL**: 190 permissions

## High-Risk Permissions (Sample)


### Mobile Device Access
- **ID**: `ADMI_MOBILE_ACCESS`
- **Categories**: user_admin, system_admin
- **Levels Granted**: Full
- **Used by 14 roles**

### View Login Audit Trail
- **ID**: `ADMI_AUDITLOGIN`
- **Categories**: user_admin, system_admin
- **Levels Granted**: Full
- **Used by 3 roles**

### Core Administration Permissions
- **ID**: `ADMI_KERNEL`
- **Categories**: user_admin, system_admin
- **Levels Granted**: Full
- **Used by 1 roles**

### Log in using Access Tokens
- **ID**: `ADMI_LOGIN_OAUTH`
- **Categories**: user_admin, system_admin
- **Levels Granted**: Full
- **Used by 1 roles**

### Manage Custom Permissions
- **ID**: `ADMI_MANAGEPERMISSIONS`
- **Categories**: user_admin, system_admin
- **Levels Granted**: Full
- **Used by 1 roles**

### Bulk Manage Roles
- **ID**: `ADMI_MANAGEROLES`
- **Categories**: role_admin
- **Levels Granted**: Full
- **Used by 1 roles**

### User Access Tokens
- **ID**: `ADMI_MANAGE_OWN_OAUTH_TOKENS`
- **Categories**: user_admin
- **Levels Granted**: Full
- **Used by 1 roles**

## SOD-Relevant Permission Categories


### Transaction Entry (93 permissions)

- **Installment Payment Links** (`LIST_INSTALLMENT_PAYMENT_LINKS`) - View - Used by 18 roles
- **Invoice** (`TRAN_CUSTINVC`) - Edit, Full, View - Used by 18 roles
- **Customer Payment** (`TRAN_CUSTPYMT`) - Edit, Full, View - Used by 18 roles
- **Find Transaction** (`TRAN_FIND`) - Full, View - Used by 18 roles
- **Credit Memo** (`TRAN_CUSTCRED`) - Create, Edit, Full, View - Used by 17 roles
- **Customer Deposit** (`TRAN_CUSTDEP`) - Full, View - Used by 17 roles
- **Customer Refund** (`TRAN_CUSTRFND`) - Create, Edit, Full, View - Used by 17 roles
- **Item Fulfillment** (`TRAN_ITEMSHIP`) - Full, View - Used by 17 roles
- **Make Journal Entry** (`TRAN_JOURNAL`) - Edit, Full, View - Used by 17 roles
- **Return Authorization** (`TRAN_RTNAUTH`) - Create, Edit, Full, View - Used by 17 roles

### Transaction Approval (10 permissions)

- **Return Authorization** (`TRAN_RTNAUTH`) - Create, Edit, Full, View - Used by 17 roles
- **Return Authorization Reports** (`REPO_RETURNAUTH`) - View - Used by 13 roles
- **Journal Approval** (`TRAN_JOURNALAPPRV`) - Full, View - Used by 13 roles
- **Invoice Approval** (`TRAN_CUSTINVCAPPRV`) - Create, Full, View - Used by 12 roles
- **Sales Order Approval** (`TRAN_SALESORDAPPRV`) - Create, View - Used by 12 roles
- **Return Auth. Approval** (`TRAN_RTNAUTHAPPRV`) - Full, View - Used by 11 roles
- **Vendor Bill Approval** (`TRAN_VENDBILLAPPRV`) - Full, View - Used by 6 roles
- **Vendor Return Auth. Approval** (`TRAN_VENDAUTHAPPRV`) - Full, View - Used by 5 roles
- **Vendor Return Authorization** (`TRAN_VENDAUTH`) - Full, View - Used by 3 roles
- **Revenue Arrangement Approval** (`TRAN_REVARRNGAPPRV`) - Create, View - Used by 2 roles

### Transaction Payment (9 permissions)

- **Installment Payment Links** (`LIST_INSTALLMENT_PAYMENT_LINKS`) - View - Used by 18 roles
- **Customer Payment** (`TRAN_CUSTPYMT`) - Edit, Full, View - Used by 18 roles
- **Check** (`TRAN_CHECK`) - View - Used by 12 roles
- **Accounts Payable Graphing** (`GRAP_AP`) - View - Used by 11 roles
- **Payment Methods** (`LIST_PAYMETH`) - Edit, Full, View - Used by 11 roles
- **Accounts Payable Register** (`REGT_ACCTPAY`) - Edit, Full, View - Used by 11 roles
- **Accounts Payable** (`REPO_AP`) - View - Used by 11 roles
- **Pay Sales Tax** (`TRAN_TAXPYMT`) - Edit, Full, View - Used by 10 roles
- **Pay Bills** (`TRAN_VENDPYMT`) - Edit, Full, View - Used by 8 roles

### Bank Reconciliation (13 permissions)

- **Generate Statements** (`TRAN_STATEMENT`) - Full, View - Used by 15 roles
- **Financial Statements** (`REPO_FINANCIALS`) - View - Used by 13 roles
- **Income Statement** (`REPO_PANDL`) - View - Used by 13 roles
- **Statement Charge** (`TRAN_CUSTCHRG`) - Full, View - Used by 13 roles
- **Reconcile** (`TRAN_RECONCILE`) - Full, View - Used by 13 roles
- **Bank Account Registers** (`REGT_BANK`) - View - Used by 12 roles
- **Cash Flow Statement** (`REPO_CASHFLOW`) - View - Used by 12 roles
- **Reconcile Reporting** (`REPO_RECONCILE`) - View - Used by 10 roles
- **Import Online Banking File** (`TRAN_IMPORTOLBFILE`) - Full, View - Used by 7 roles
- **Financial Statement Sections** (`ADMI_REPOGROUPS`) - Full - Used by 4 roles

### Vendor Setup (5 permissions)

- **Vendors** (`LIST_VENDOR`) - Edit, Full, View - Used by 14 roles
- **Enter Vendor Credits** (`TRAN_VENDCRED`) - Full, View - Used by 11 roles
- **Vendor Return Auth. Approval** (`TRAN_VENDAUTHAPPRV`) - Full, View - Used by 5 roles
- **Vendor Return Authorization** (`TRAN_VENDAUTH`) - Full, View - Used by 3 roles
- **Vendor Returns** (`TRAN_VENDAUTHRETURN`) - Full, View - Used by 3 roles

### User Admin (12 permissions)

- **Other Lists** (`ADMI_EMPLOYEELIST`) - Full, View - Used by 17 roles
- **Imported Employee Expenses** (`LIST_IMPORTED_EMPLOYEE_EXPENSE`) - View - Used by 14 roles
- **Employee Reminders** (`REPO_REMINDEREMPLOYEE`) - View - Used by 14 roles
- **Mobile Device Access** (`ADMI_MOBILE_ACCESS`) - Full - Used by 14 roles
- **Employees** (`LIST_EMPLOYEE`) - Full, View - Used by 13 roles
- **Employee Record** (`LIST_EMPLOYEE_RECORD`) - Full, View - Used by 13 roles
- **View Login Audit Trail** (`ADMI_AUDITLOGIN`) - Full - Used by 3 roles
- **Core Administration Permissions** (`ADMI_KERNEL`) - Full - Used by 1 roles
- **Log in using Access Tokens** (`ADMI_LOGIN_OAUTH`) - Full - Used by 1 roles
- **Manage Custom Permissions** (`ADMI_MANAGEPERMISSIONS`) - Full - Used by 1 roles

### Role Admin (2 permissions)

- **Contact Roles** (`LIST_CONTACTROLE`) - Full, View - Used by 6 roles
- **Bulk Manage Roles** (`ADMI_MANAGEROLES`) - Full - Used by 1 roles