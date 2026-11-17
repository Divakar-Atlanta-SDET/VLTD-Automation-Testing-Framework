# VLTD Admin Panel -- Complete Module & Functional Explanation

## 1. Purpose

This document consolidates the functional understanding of the VLTD
(Vehicle Location Tracking Device) Admin/TC panel from the application
exploration completed so far. It is intended as a QA reference for
functional testing, regression planning, automation design, API
validation and exploratory testing.

> Only business rules explicitly confirmed during exploration are
> treated as requirements. Areas whose detailed behavior has not yet
> been confirmed are marked accordingly rather than being assumed.

------------------------------------------------------------------------

# 2. Application Overview

The VLTD application supports tracking and administration of
commercial/public vehicles equipped with AIS-140 compliant Vehicle
Location Tracking Devices (VLTDs).

The Admin/TC panel covers:

-   Vehicle/device tracking
-   GIS and geofencing
-   Emergency response
-   Ownership and account operations
-   Device operations
-   Public transport information management
-   Challan management
-   OEM/FC/user administration
-   System configuration
-   Device/compliance/alert/fleet reporting
-   Helpdesk

Major panel areas:

1.  Dashboard
2.  Control & Operations
3.  Administration
4.  Reports
5.  Helpdesk
6.  Miscellaneous

------------------------------------------------------------------------

# 3. Roles / Actors

The system interacts with:

-   Admin / Transport Commissioner (TC)
-   OEM
-   Fitment Center (FC)
-   Inspector
-   Driver
-   Staff
-   RTO
-   Permit Holder
-   Vehicle Owner / Account
-   Support Team
-   Emergency Help Centre personnel

Role-based access is a major QA concern because many records are created
by one role and managed or approved by another.

------------------------------------------------------------------------

# 4. Dashboard

## KPI Cards

The dashboard contains:

-   AIS-140 Fitted Vehicles
-   Currently Active AIS-140 Fitments
-   Inactive Fitted Vehicles
-   Never Sent Data
-   Active Alerts
-   Challans This Month

## QA Focus

Validate:

-   KPI calculation accuracy
-   UI/API consistency
-   Zero/null values
-   Large values
-   Refresh behavior
-   Date-dependent values
-   Navigation from KPI cards where applicable
-   Consistency with underlying reports/lists
-   Role-based visibility

A strong regression check is to reconcile dashboard KPI values with
API/database data.

------------------------------------------------------------------------

# 5. CONTROL & OPERATIONS

Control & Operations is a major area and contains:

1.  Tracking & GIS
2.  Command Center
3.  Vehicle Ownership Transfer
4.  Account Merge
5.  Vehicle Device Untag
6.  PIS Management
7.  Challan Management
8.  Announcements

------------------------------------------------------------------------

## 5.1 Tracking & GIS

Submodules:

-   Live Tracking
-   Geofences
-   Trip Playback
-   Alerts
-   ERSS Dashboard
-   Help Centres

------------------------------------------------------------------------

## 5.1.1 Live Tracking

### Purpose

Provides real-time vehicle location and telemetry.

### Confirmed/Observed Functions

-   Vehicle/IMEI search
-   Status filters:
    -   Moving
    -   Idle
    -   Stopped
    -   Offline
    -   No GPS
    -   SOS
-   Vehicle cards
-   Map
-   Vehicle details
-   Speed
-   Ignition
-   GPS information
-   Vehicle assignment
-   Alerts
-   Fit Data
-   Map/layer controls

### QA Focus

-   Search by vehicle/IMEI
-   Status filtering
-   Moving/idle/stopped accuracy
-   Offline detection
-   No-GPS handling
-   SOS visibility
-   Last-known location
-   Telemetry freshness
-   Speed/ignition consistency
-   Vehicle-device mapping
-   Map marker accuracy
-   Empty/invalid search
-   Multiple vehicle handling
-   Refresh
-   RBAC and API authorization

### High-Risk Defects

-   Wrong vehicle telemetry displayed
-   Stale data shown as live
-   Offline device shown as active
-   GPS unavailable but stale coordinates presented as current
-   Unauthorized vehicle data exposure

------------------------------------------------------------------------

## 5.1.2 Geofences

### Purpose

Create geographic boundaries and generate entry/exit alerts for
associated vehicles.

### Functions

-   Create
-   View
-   Edit
-   Delete
-   Vehicle association
-   Entry detection
-   Exit detection
-   Alert generation

### QA Focus

-   Required fields
-   Boundary accuracy
-   Coordinates
-   Map selection
-   Vehicle association
-   Entry/exit detection
-   Overlapping geofences
-   Multiple geofences
-   GPS unavailable
-   Duplicate/repeated alerts
-   Search/filter if available
-   Authorization

### Boundary Tests

Test:

-   Exactly on boundary
-   Just inside
-   Just outside
-   Rapid crossing
-   GPS movement around boundary

------------------------------------------------------------------------

## 5.1.3 Trip Playback

### Purpose

View historical movement of a vehicle.

### QA Focus

-   Vehicle selection
-   Date/time selection
-   Historical telemetry
-   Start/end timestamps
-   Playback
-   Missing telemetry
-   Timezone
-   No-data behavior
-   Large date ranges
-   Vehicle authorization

Critical check: historical data must belong to the selected
vehicle/device.

------------------------------------------------------------------------

## 5.1.4 Alerts

### Purpose

View vehicle-related alerts.

### QA Focus

-   Alert listing
-   Alert type
-   Vehicle
-   Timestamp
-   Search/filter
-   Details
-   Duplicate alerts
-   Status/acknowledgement if implemented
-   Pagination
-   Date filtering
-   Authorization
-   Consistency with Alert Report and Vehicle Alert Trail

Detailed acknowledgement/escalation rules should be validated against
the final requirement if introduced.

------------------------------------------------------------------------

## 5.1.5 ERSS Dashboard

### Purpose

Emergency Response Support System workflow.

Confirmed conceptual flow:

1.  Person in distress presses help/SOS button.
2.  Emergency alert is generated.
3.  Vehicle/location information is associated with the alert.
4.  Emergency information is directed toward the nearest Help Centre.

### QA Focus

-   SOS event generation
-   Alert creation
-   Vehicle identification
-   Current/latest location
-   Timestamp
-   Nearest Help Centre
-   Correct centre selection
-   Alert delivery
-   Duplicate SOS
-   GPS unavailable
-   No Help Centre
-   Multiple/equal-distance centres
-   Stale location
-   Persistence
-   Acknowledgement/escalation if implemented
-   Response time
-   Authorization

### Critical Risks

-   Wrong vehicle
-   Wrong coordinates
-   Wrong nearest centre
-   No response when no centre exists
-   Duplicate emergency events
-   Stale location
-   Unauthorized emergency-data access

------------------------------------------------------------------------

## 5.1.6 Help Centres

### Purpose

Manage emergency response Help Centres used by ERSS.

### Confirmed Create Fields

-   Name -- required
-   Type -- required
-   Category -- required
-   City -- required
-   RTO -- optional
-   Exact Location -- required
-   Location search
-   Map
-   Pin/map-center selection

### QA Focus

-   Required validation
-   Name/type/category
-   City/RTO relationship
-   Location search
-   Latitude/longitude persistence
-   Map pin accuracy
-   Duplicate centre handling
-   Search by name/address
-   ERSS relationship
-   Nearest-centre calculation

------------------------------------------------------------------------

# 5.2 Command Center

Contains:

-   Command List
-   Command Center

Detailed command types, state transitions and payload behavior have not
yet been fully confirmed.

### Initial QA Coverage

-   Page accessibility
-   Authorization
-   List loading
-   Search/filter where available
-   Pagination
-   Command submission once behavior is confirmed
-   Success/failure handling
-   Duplicate command handling
-   Audit/history if available

Do not invent command-specific business expectations until requirements
are confirmed.

------------------------------------------------------------------------

# 5.3 Vehicle Ownership Transfer

### Purpose

Transfer a vehicle from its current owner/account to another account
using an RTO transfer certificate.

### Search

-   Registration Number
-   Vehicle ID

### Flow

1.  Search vehicle.
2.  Verify current owner.
3.  Select target owner.
4.  Provide RTO transfer certificate.
5.  Execute transfer.
6.  Verify new ownership.

### QA Focus

-   Valid/invalid vehicle
-   Current owner
-   Target account
-   Same source/target
-   Non-existent target
-   Supporting certificate
-   Missing/invalid certificate
-   Already transferred vehicle
-   Ownership persistence
-   Old owner access
-   New owner access
-   Audit/history
-   Report entry
-   RBAC/API authorization

### Data Integrity

After transfer, the vehicle must not remain incorrectly associated with
both owners.

------------------------------------------------------------------------

# 5.4 Account Merge

### Purpose

Merge multiple accounts belonging to the same user into one destination
account.

### Confirmed Business Rules

After successful merge:

-   Source account is deactivated.
-   Destination account remains active.
-   Source vehicles are transferred to destination.

### Search

-   Mobile number
-   Email
-   Account ID

### QA Focus

-   Source/destination search
-   Same account
-   Different users
-   Invalid account
-   Inactive source
-   Active destination
-   Zero/multiple vehicles
-   Duplicate vehicle association
-   Merge confirmation
-   Vehicle migration
-   Source deactivation
-   Destination remains active
-   Partial failure/rollback
-   Repeated merge
-   Audit
-   Report
-   Authorization

High-risk area: partial failure must not leave inconsistent
account/vehicle relationships.

------------------------------------------------------------------------

# 5.5 Vehicle Device Untag

### Purpose

Remove the currently tagged VLTD device from a vehicle.

### Search

Registration Number.

### Flow

1.  Find Vehicle.
2.  Search registration number.
3.  View vehicle details/current device.
4.  Perform administrative untag.

### QA Focus

-   Valid/invalid registration
-   Vehicle with no device
-   Active device
-   Confirmation
-   Successful untag
-   Repeated untag
-   Vehicle/device relationship
-   Tracking impact
-   Device status
-   Historical telemetry retention
-   Audit
-   API/RBAC authorization

Historical telemetry should not be assumed to disappear unless
explicitly required.

------------------------------------------------------------------------

# 5.6 Operations -- PIS Management

PIS = Public Information System.

Submodules:

1.  Stop Management
2.  Route Management
3.  Service Calendar Management
4.  Service Pattern Management
5.  Time Table Management
6.  Trip Management

### Dependency Chain

``` text
Stop
  ↓
Route
  ↓
Service Calendar
  ↓
Service Pattern
  ↓
Time Table
  ↓
Trip
  ↓
Vehicle + Driver
```

This is one of the most important cross-module regression chains.

------------------------------------------------------------------------

## 5.6.1 Stop Management

### Functions

-   List
-   Search
-   City/status filters
-   Pagination
-   Refresh
-   Reset
-   Create
-   Activate/deactivate
-   Bulk upload

### Create Fields

-   City -- required
-   Stop Code -- required
-   Stop Name -- required
-   Address
-   Latitude -- required
-   Longitude -- required
-   Active Status
-   Map location/search

### QA Focus

-   Required validation
-   Stop-code uniqueness
-   Coordinates/ranges
-   Map selection
-   Active/inactive
-   Search/filter
-   Pagination
-   Refresh/reset
-   Edit if available
-   Bulk upload
-   Duplicate stops

------------------------------------------------------------------------

## 5.6.2 Route Management

### Functions

-   Search by Route Code/Name
-   Active filter
-   Visibility filter
-   Pagination
-   Refresh/reset
-   Create

### Create Fields

-   Route Code -- required
-   Route Name -- required
-   Description
-   Active Status
-   Stops -- required

### Confirmed Rule

A route requires at least **2 stops**, and stop order determines travel
order.

### QA Focus

-   Required fields
-   Route-code uniqueness
-   Minimum 2 stops
-   Stop ordering
-   Duplicate stops
-   Reordering
-   Active status
-   Visibility
-   Search/filter
-   Edit
-   Route-stop relationship

------------------------------------------------------------------------

## 5.6.3 Service Calendar Management

### Create Fields

-   Calendar Name -- required
-   Active Status
-   Operating days Monday--Sunday
-   Effective From -- required
-   Effective To -- optional
-   Exceptions after creation

### Confirmed Rule

At least one operating day must be selected.

### QA Focus

-   Name
-   Day selection
-   One/all days
-   Effective dates
-   From \> To
-   Same date
-   Past/future dates
-   Exceptions
-   Active/inactive
-   Edit
-   Duplicate calendars

------------------------------------------------------------------------

## 5.6.4 Service Pattern Management

### Create Fields

-   Route -- required
-   Service Calendar -- required
-   Service Code -- required
-   Service Name -- required
-   Direction -- required
-   Active Status

### QA Focus

-   Required fields
-   Route/calendar dependencies
-   Service-code uniqueness
-   Direction
-   Active status
-   Inactive dependencies
-   Edit
-   Duplicate pattern
-   Timetable compatibility

------------------------------------------------------------------------

## 5.6.5 Time Table Management

### Create Fields

-   Service Pattern -- required
-   Timetable Name -- required
-   Schedule Type -- required
-   Start Time -- required
-   End Time -- required
-   Headway -- optional, minutes
-   Valid From -- required
-   Valid To -- optional
-   Active Status

### Confirmed Behavior

Timetable stops are ordered. Stop identity and sequence are tied to the
selected route. Arrival/departure offsets are minutes from timetable
start.

### QA Focus

-   Required fields
-   Start/end time
-   End before start
-   Same start/end
-   Headway boundaries
-   Stop order
-   Route consistency
-   Offset values/order
-   Validity dates
-   Active status
-   Edit
-   Trip compatibility

------------------------------------------------------------------------

## 5.6.6 Trip Management

### List KPIs

-   Total Trips
-   Scheduled
-   In Progress
-   Completed

### Filters

-   Timetable
-   Service Date
-   Status
-   Page size

### Create Fields

-   Timetable -- required
-   Service Date -- required
-   Vehicle -- required
-   Driver -- required

### QA Focus

-   Required fields
-   Valid timetable
-   Service date
-   Vehicle
-   Driver
-   Inactive vehicle/driver behavior
-   Duplicate trip
-   Status transitions
-   KPI updates
-   Pagination/filter
-   Timetable relationship

### Critical E2E

Create and verify:

**Stop → Route → Calendar → Service Pattern → Timetable → Trip**

------------------------------------------------------------------------

# 5.7 Challan Management

Contains:

-   Challan Master
-   Challan Work Queue

------------------------------------------------------------------------

## 5.7.1 Challan Master

### Dashboard KPIs

-   Total Types
-   Active
-   Inactive
-   Compoundable

### Create Fields

-   Challan Code -- required
-   Challan Name -- required
-   Description
-   Penalty Amount -- required
-   Legal Reference
-   Compoundable Offence
-   Effective From
-   Effective To
-   Active Status

### Example Discussed

Device Not Installed / Motor Vehicle Act Section 183 / ₹5,000 /
Compoundable / Active.

### QA Focus

-   Required fields
-   Code uniqueness
-   Penalty amount
-   Zero/negative values
-   Legal reference
-   Compoundable state
-   Effective dates
-   Active/inactive
-   Edit
-   KPI accuracy
-   Search/filter
-   Duplicate offence

------------------------------------------------------------------------

## 5.7.2 Challan Work Queue

### Purpose

View, approve or cancel challans.

### QA Focus

-   Listing
-   Search/filter
-   Details
-   Approve
-   Cancel
-   Invalid state transition
-   Duplicate action
-   Refresh
-   Persistence
-   Authorization
-   Audit/history
-   Relationship to Challan Master

Exact state-transition rules should be confirmed before exhaustive
automation.

------------------------------------------------------------------------

# 5.8 Announcements

Announcements are present under Operations, but detailed
create/edit/publish/targeting rules were not fully confirmed.

Initial testing:

-   Page access
-   Authorization
-   Listing
-   Search/filter if available
-   Pagination
-   Open/view
-   Create/edit/publish after requirements are confirmed
-   Expiry/visibility if implemented

------------------------------------------------------------------------

# 6. ADMINISTRATION

## 6.1 Fitment Center Management

Admin/TC can:

-   View/list
-   Approve
-   Blacklist

Admin/TC cannot create Fitment Centers.

### Business Flow

**OEM creates FC → Admin approves or blacklists FC**

### QA

-   Listing/search/filter
-   Approval
-   Blacklist
-   Status persistence
-   OEM relationship
-   RBAC
-   Direct URL/API authorization
-   Audit

------------------------------------------------------------------------

## 6.2 OEM Management

### Actions

-   Register
-   View
-   Edit
-   Blacklist
-   Suspend

### Registration Fields

-   Business Name
-   OEM Code
-   CIN
-   GST Number
-   GST Certificate
-   TAC Name
-   TAC Number
-   TAC Certificate
-   COP Name
-   COP Plan
-   COP Valid Till
-   COP Certificate
-   Office Address
-   Contact information
-   Password
-   Confirm Password

### QA

-   Required fields
-   OEM-code uniqueness
-   CIN/GST validation
-   Certificate file type/size
-   TAC/COP information
-   Expiry dates
-   Password policy
-   Duplicate OEM
-   Edit
-   Suspend
-   Blacklist
-   Status transitions
-   Access impact
-   Audit

------------------------------------------------------------------------

## 6.3 Inspector Management

Actions:

-   Create
-   Transfer

### QA

-   Required fields
-   Unique identifier
-   Duplicate
-   Create/view/edit where available
-   Transfer
-   Invalid destination
-   Old/new assignment
-   Status
-   Audit
-   RBAC

------------------------------------------------------------------------

## 6.4 Driver Management

Actions:

-   View
-   Create
-   Audit
-   Edit
-   Deactivate
-   Suspend

### Create Fields

-   Driver Name -- required
-   Email -- required
-   Contact Number -- required
-   Driver Licence Number -- required
-   State
-   City
-   Address
-   Initial Password -- required
-   Confirm Password -- required
-   Driver Licence
-   Driver Photo -- required, max 5 MB

### Password Rule Observed

Minimum 10 characters with uppercase, lowercase, number and symbol.

### QA

-   Required fields
-   Email/contact validation
-   Duplicate email
-   Duplicate licence
-   Password policy
-   Confirm password
-   Photo/file validation
-   5 MB boundary
-   Edit
-   Suspend
-   Deactivate
-   Audit
-   Authentication creation

------------------------------------------------------------------------

## 6.5 Staff Management

Actions:

-   Create
-   Edit
-   View
-   Suspend
-   Unsuspend
-   Blacklist

### Confirmed Lifecycle Rule

-   Suspended staff can be unsuspended.
-   Blacklisted staff can never be reactivated.

### QA

-   Active → Suspended
-   Suspended → Active
-   Active → Blacklisted
-   Blacklisted → reactivation attempt rejected
-   Duplicate
-   Edit
-   Search/filter
-   Status persistence
-   Authorization
-   Audit

------------------------------------------------------------------------

## 6.6 RTO Management

Actions:

-   Register
-   Edit

### Fields

-   RTO Name
-   RTO Code
-   Contact Number
-   Contact Email
-   Address
-   District
-   Pincode
-   Map location/search
-   Description
-   Password
-   Confirm Password

### QA

-   Required fields
-   RTO-code uniqueness
-   Email/contact
-   Pincode
-   Location
-   Password policy
-   Duplicate RTO
-   Edit
-   Authentication
-   Audit

------------------------------------------------------------------------

## 6.7 Permit Holder

Permit Holder is created by Fitment Center during fitment.

Admin can view/search/filter but cannot:

-   Create
-   Suspend
-   Blacklist

### QA

-   View-only behavior
-   Search/filter
-   Vehicle relationship
-   FC relationship
-   RTO/city relationship
-   RBAC
-   Direct URL/API authorization

------------------------------------------------------------------------

# 7. SYSTEM CONFIGURATION

Contains:

-   Settings
-   Change Log

------------------------------------------------------------------------

## 7.1 Device Monitoring

Setting:

**Device Offline Alert**

Current value:

-   24 hours
-   Unit: hours
-   Active/Inactive

Expected behavior: when a device stops transmitting, an alert is
expected for the vehicle's own account and the Transport Commissioner.

### QA

-   Save
-   Enable/disable
-   Persistence
-   Exact threshold
-   Just below/above threshold
-   Alert timing
-   Alert recipients
-   Zero/negative/decimal/text/large values

------------------------------------------------------------------------

## 7.2 Compliance Reminders

Settings:

-   COP Expiry Reminder
-   TAC Expiry Reminder

Current reminder:

-   30 days before expiry
-   Days-before setting
-   Active/Inactive

### QA

-   Exact 30-day boundary
-   29/31 days
-   Custom value
-   Disable
-   Persistence
-   Duplicate reminder prevention
-   Expired certificate
-   Change Log

------------------------------------------------------------------------

## 7.3 Location Validation

Rules:

-   Fitment Centre → Vehicle maximum distance: 1000 m
-   Inspector → Vehicle maximum distance: 1000 m
-   RTO → Vehicle maximum distance: 1000 m

### QA

For each rule:

-   Exactly 1000 m
-   Less than 1000 m
-   Greater than 1000 m
-   Zero
-   Negative
-   Decimal
-   Very large
-   Text
-   Active/inactive
-   Persistence
-   Actual business-rule enforcement
-   API bypass

------------------------------------------------------------------------

## 7.4 Change Log

Validate:

-   Setting name
-   Old value
-   New value
-   Actor
-   Timestamp
-   Multiple changes
-   No false entries
-   Immutable history
-   Authorization

------------------------------------------------------------------------

# 8. REPORTS

## 8.1 Ownership Transfer Report

Filters:

-   Search
-   From Date
-   To Date
-   Type
-   Reason
-   Clear Filters
-   Refresh
-   Export Excel

Validate:

-   Vehicle
-   Old/new owner
-   Transfer date/time
-   Reason/type
-   Actor
-   Certificate/reference
-   Date boundaries
-   Export
-   Pagination

------------------------------------------------------------------------

## 8.2 Account Merge Report

Validate:

-   Source
-   Destination
-   Vehicle count
-   Reason
-   Actor/authority
-   Status
-   Date/time
-   Export
-   Pagination

------------------------------------------------------------------------

## 8.3 Device Packets

Categories:

-   Stored Packets
-   Raw Packets
-   Rejected Packets

Filters:

-   IMEI
-   From/To date/time
-   Quick ranges
-   Pagination
-   Rows per page

Possible packet fields:

-   Received time
-   GPS time
-   IMEI
-   Vehicle
-   Packet type
-   Alert
-   GPS
-   Latitude/longitude
-   Speed
-   Heading
-   Satellites
-   HDOP
-   Ignition
-   Battery
-   Other packet values

QA:

-   Correct category
-   Classification
-   Timestamp
-   IMEI/vehicle mapping
-   Date/time
-   Pagination
-   Large datasets
-   Empty result
-   Export if available

------------------------------------------------------------------------

## 8.4 Device Status & Connectivity

Validate:

-   Online/offline
-   Last seen
-   Device mapping
-   Offline threshold
-   Online → offline
-   Offline → online

Cross-check with Device Offline Alert configuration.

------------------------------------------------------------------------

## 8.5 Device Health Report

Validate:

-   Device search
-   Health status
-   Metrics
-   Null/missing values
-   Date filter
-   Mapping
-   Pagination

------------------------------------------------------------------------

## 8.6 SIM Validity Report

Validate:

-   SIM-device relationship
-   Valid
-   Expired
-   Near expiry
-   Expiry date
-   Search/filter
-   Pagination
-   Empty state

------------------------------------------------------------------------

## 8.7 Alert Report

Validate:

-   Vehicle
-   Alert type
-   Date
-   Timestamp
-   Source
-   Duplicates
-   Search/filter
-   Pagination

------------------------------------------------------------------------

## 8.8 Vehicle Alert Trail

Validate:

-   Chronological history
-   Vehicle
-   Alert
-   Timestamp
-   Status/details
-   Date filtering
-   Consistency with Alert Report

------------------------------------------------------------------------

## 8.9 Alert Set History

Validate:

-   Creation
-   Modification
-   Actor
-   Timestamp
-   Old/new configuration where applicable
-   Immutable history

------------------------------------------------------------------------

## 8.10 Multiple-Challan Vehicle Report

Filters:

-   From Date
-   To Date
-   Minimum Challans
-   Sort By
-   Sort Direction
-   Per Page

Output:

-   Vehicle
-   Count
-   Status Breakdown
-   Configured Penalties
-   First Challan
-   Last Challan

QA:

-   Threshold below/exactly/above
-   Date boundaries
-   Status calculation
-   Penalty calculation
-   Ascending/descending
-   Pagination
-   Empty result

------------------------------------------------------------------------

## 8.11 Fleet Activity

KPIs:

-   Tracked Vehicles
-   Moving
-   Idle
-   SOS
-   Offline

Ranges:

-   Today
-   Last 24h
-   Last 7d
-   Last 30d
-   Custom

Search:

-   Vehicle
-   IMEI

Table:

-   Vehicle
-   Live Status
-   Last Seen
-   Driver
-   Distance
-   Driving Time
-   Trips
-   Alerts

Export Excel is available.

### High-Value Reconciliation

Validate:

**Dashboard KPI ↔ Fleet Activity KPI ↔ underlying vehicle data**

------------------------------------------------------------------------

## 8.12 Installation & Maintenance Reports

Reports:

-   Installation Performance
-   Installation Report
-   Repair & Replacement

### Repair & Replacement Critical Flow

``` text
Old Device
   ↓
Replacement
   ↓
New Active Mapping
   ↓
New Device Status/Packets
   ↓
Fleet/Tracking Reports
```

Validate that the old device does not remain incorrectly active for the
vehicle.

------------------------------------------------------------------------

## 8.13 Watch History

Records:

-   Vehicle added to watchlist
-   Vehicle removed from watchlist

Expected history data:

-   Vehicle
-   Watchlist
-   Activity
-   Actor
-   Timestamp

### Excellent Automation Candidate

1.  Add vehicle.
2.  Verify ADD history.
3.  Remove vehicle.
4.  Verify REMOVE history.
5.  Verify actor/timestamp.

------------------------------------------------------------------------

# 9. HELPDESK

Helpdesk contains tickets raised by the support team. Admin can follow
progress and take permitted actions.

## Support Queue

Controls/fields:

-   Search
-   Status
-   Priority
-   From Date
-   To Date
-   Reset Filters
-   Refresh
-   Ticket code
-   Title/description
-   Status
-   Priority
-   Raised by
-   Assigned to
-   Submitted via
-   Created date
-   Actions

### QA

-   Listing
-   Search
-   Status filter
-   Priority filter
-   Date range
-   Reset
-   Refresh
-   Open ticket
-   Actions
-   Status transitions
-   Assignment
-   Authorization
-   Pagination
-   Persistence
-   Audit/history

------------------------------------------------------------------------

# 10. MISCELLANEOUS

Includes:

-   Profile
-   Tickets
-   What's New
-   Logout
-   Navigation styles

Navigation styles discussed:

-   Dropdown Navigation
-   Mega Navigation
-   Hub Navigation

### QA

Navigation:

-   Correct visibility
-   Correct routing
-   No broken links
-   Role-based visibility
-   Direct URL protection

Logout:

-   Session invalidation
-   Redirect to login
-   Protected pages cannot be reopened from cache/back
-   Protected APIs require valid authentication

------------------------------------------------------------------------

# 11. MAJOR BUSINESS DEPENDENCIES

## PIS

``` text
Stop
 ↓
Route
 ↓
Service Calendar
 ↓
Service Pattern
 ↓
Time Table
 ↓
Trip
 ↓
Vehicle + Driver
```

## Fitment / Device

``` text
OEM
 ↓
Fitment Center
 ↓
Vehicle Fitment
 ↓
VLTD Device
 ↓
Vehicle ↔ Device
 ↓
Telemetry
 ↓
Tracking / Alerts / Reports
```

## Ownership

``` text
Current Owner
 ↓
Ownership Transfer
 ↓
RTO Certificate
 ↓
New Owner
 ↓
Access / Tracking / Reports
```

## Account Merge

``` text
Source Account
 ↓
Account Merge
 ↓
Vehicles moved
 ↓
Source deactivated
 ↓
Destination remains active
```

## Emergency Response

``` text
Vehicle
 ↓
SOS / Help Button
 ↓
Emergency Alert
 ↓
Vehicle Location
 ↓
Nearest Help Centre
 ↓
Emergency Response
```

------------------------------------------------------------------------

# 12. HIGH-RISK QA PRIORITY

## Critical

-   Live Tracking
-   ERSS Dashboard
-   Ownership Transfer
-   Account Merge
-   Device Untag
-   Device Replacement
-   Authentication/RBAC
-   Configuration enforcement

## High

-   PIS dependency chain
-   Challan Work Queue
-   OEM
-   Staff lifecycle
-   Driver lifecycle
-   Device Status
-   Fleet Activity
-   Alert Reports
-   Watch History

## Medium

-   RTO
-   Inspector
-   Helpdesk
-   Standard CRUD/filter regression
-   Announcements
-   Navigation

------------------------------------------------------------------------

# 13. AUTOMATION STRATEGY

Do not automate every manual test as a separate UI script.

Recommended layers:

## Smoke

Approximately 15--25 tests covering:

-   Login
-   Dashboard
-   Critical navigation
-   One representative CRUD
-   One status workflow
-   Configuration save
-   One report
-   One critical E2E
-   Logout

## Regression

Approximately 60--100 logical scenarios, using parameterization and
reusable components.

Coverage:

-   Administration
-   Control & Operations
-   PIS
-   Configuration
-   Reports
-   Helpdesk
-   Authentication/RBAC

## Critical E2E

Recommended flows:

1.  OEM → Fitment Center → approval
2.  Ownership transfer → report verification
3.  Account merge → vehicle migration
4.  Device untag → mapping verification
5.  Stop → Route → Calendar → Pattern → Timetable → Trip
6.  Device replacement → new mapping → reports/status
7.  SOS → ERSS → Help Centre
8.  Watchlist add/remove → history

------------------------------------------------------------------------

# 14. API / DATABASE VALIDATION

For critical workflows, UI success is not enough.

Validate:

-   HTTP status code
-   Response schema
-   Response time
-   Authorization
-   Invalid payload
-   Duplicate handling
-   Null handling
-   Data integrity
-   Pagination metadata
-   Token/session behavior
-   Idempotency
-   Database state
-   Audit records

Example:

``` text
Ownership Transfer
       ↓
UI success
       ↓
API/DB validation
       ↓
Vehicle.owner_id = new owner
       ↓
Old owner no longer has access
       ↓
New owner has access
       ↓
Transfer report created
       ↓
Audit entry created
```

------------------------------------------------------------------------

# 15. RECOMMENDED PLAYWRIGHT + PYTEST STRUCTURE

``` text
vltd_automation/
│
├── tests/
│   ├── smoke/
│   ├── regression/
│   ├── e2e/
│   │
│   ├── administration/
│   │   ├── test_oem.py
│   │   ├── test_fitment_center.py
│   │   ├── test_inspector.py
│   │   ├── test_driver.py
│   │   ├── test_staff.py
│   │   ├── test_rto.py
│   │   └── test_permit_holder.py
│   │
│   ├── control_operations/
│   │   ├── test_live_tracking.py
│   │   ├── test_geofences.py
│   │   ├── test_trip_playback.py
│   │   ├── test_alerts.py
│   │   ├── test_erss.py
│   │   ├── test_help_centres.py
│   │   ├── test_ownership_transfer.py
│   │   ├── test_account_merge.py
│   │   ├── test_device_untag.py
│   │   ├── test_stop_management.py
│   │   ├── test_route_management.py
│   │   ├── test_service_calendar.py
│   │   ├── test_service_pattern.py
│   │   ├── test_timetable.py
│   │   ├── test_trip_management.py
│   │   └── test_challan.py
│   │
│   ├── configuration/
│   │   └── test_system_configuration.py
│   │
│   ├── reports/
│   │   ├── test_ownership_transfer_report.py
│   │   ├── test_account_merge_report.py
│   │   ├── test_device_reports.py
│   │   ├── test_alert_reports.py
│   │   ├── test_compliance_report.py
│   │   ├── test_fleet_activity.py
│   │   ├── test_installation_reports.py
│   │   └── test_watch_history.py
│   │
│   └── helpdesk/
│       └── test_helpdesk.py
│
├── pages/
│   ├── login_page.py
│   ├── dashboard_page.py
│   ├── control_operations/
│   ├── administration/
│   ├── configuration/
│   ├── reports/
│   └── helpdesk/
│
├── api/
│   └── api_client.py
│
├── utils/
│   ├── test_data.py
│   ├── database.py
│   ├── assertions.py
│   └── helpers.py
│
├── data/
│   ├── users.yaml
│   ├── vehicles.yaml
│   ├── drivers.yaml
│   ├── oem.yaml
│   └── pis.yaml
│
├── conftest.py
├── pytest.ini
└── config.yaml
```

------------------------------------------------------------------------

# 16. TEST DATA STRATEGY

Avoid creating all test data through the UI.

Recommended:

``` text
API / DB
   ↓
Create test state
   ↓
Playwright
   ↓
Execute UI workflow
   ↓
API / DB
   ↓
Verify resulting state
```

Example for Staff Blacklist:

``` text
API creates staff
      ↓
UI searches staff
      ↓
UI blacklists staff
      ↓
API/DB verifies BLACKLISTED
      ↓
UI verifies reactivation is unavailable/rejected
```

This improves execution speed and reduces flaky setup.

------------------------------------------------------------------------

# 17. AUTOMATION DESIGN PRINCIPLES

Create reusable components for:

-   Login
-   Search
-   Filters
-   Pagination
-   Date pickers
-   File uploads
-   Status actions
-   Confirmation dialogs
-   Toast validation
-   Export/download
-   Table assertions
-   API calls
-   Authentication
-   Test data creation/cleanup

Use parameterization for:

-   Status values
-   Boundary values
-   Invalid inputs
-   Date ranges
-   User types
-   Report filters
-   File types

Avoid duplicate scripts for the same workflow with different data.

------------------------------------------------------------------------

# 18. IMPLEMENTATION PHASES

## Phase 1 -- Framework Foundation

-   Playwright
-   Pytest
-   Environment/config handling
-   Login fixture
-   Page Object Model
-   Reporting
-   Screenshots/video on failure
-   Logging
-   API client
-   Test data utilities

## Phase 2 -- Authentication + Administration

-   Login
-   Logout
-   OEM
-   Fitment Center
-   Driver
-   Staff
-   RTO

## Phase 3 -- Control & Operations

-   Ownership Transfer
-   Account Merge
-   Device Untag
-   Stop
-   Route
-   Service Calendar
-   Service Pattern
-   Timetable
-   Trip

## Phase 4 -- Configuration

-   Device Offline Alert
-   COP/TAC reminders
-   Location validation
-   Change Log

## Phase 5 -- Reports

Prioritize:

-   Ownership Transfer
-   Account Merge
-   Device Status
-   Alert Report
-   Fleet Activity
-   Multiple-Challan
-   Watch History

## Phase 6 -- Critical E2E

-   PIS chain
-   Ownership transfer + report
-   Account merge + vehicle verification
-   Device replacement
-   SOS/ERSS
-   Watchlist history

## Phase 7 -- API/Data Integrity

-   API assertions
-   Database verification
-   Authorization tests
-   Negative API tests
-   Idempotency tests

------------------------------------------------------------------------

# 19. FINAL QA OBJECTIVE

The objective of the automation framework should not be to automate
every possible manual test.

The goal is to make the automation suite answer, quickly and reliably:

> **Can the core VLTD administrative and operational workflows still be
> trusted after the latest build?**

The strongest automation coverage should therefore focus on:

1.  Critical business workflows
2.  CRUD operations that are repeated frequently
3.  State transitions
4.  Cross-module dependencies
5.  Data integrity
6.  RBAC/security
7.  Reports versus transactional data
8.  Configuration versus actual enforcement
9.  Vehicle/device relationships
10. Emergency workflows
11. Regression-prone operations
12. API/database verification for critical changes
