# VLTD Platform --- State Admin Workflow Explained

**Source:** *VLTD Platform --- How Everything Works*, Version 1.0.0,
October 2026\
**Purpose:** Explain the State Admin's end-to-end workflow and how the
State Admin's actions connect to the rest of the VLTD platform. This
document follows the supplied guide; where the guide describes a feature
as disabled, future-facing, or not connected, that status is called out
explicitly.

------------------------------------------------------------------------

## 1. The big picture

The VLTD platform manages AIS-140 vehicle-tracking devices from
registration and installation through live monitoring, emergency
handling, enforcement, reporting, and maintenance.

A tracking device sends a packet approximately every **10 seconds**.
Packets may contain GPS position, speed, ignition state, battery levels,
and an emergency flag. The platform checks GPS quality, processes alerts
and geofence events, and exposes the resulting information through
role-specific panels.

The State Admin is the state-level command-and-control role. The State
Admin can see every vehicle in the state and manages important
state-wide configuration and master data. However, some workflows are
performed by other roles:

-   **Super Admin:** platform setup and management of State Admins,
    OEMs, and fitment centres.
-   **State Admin:** state-wide operations, master data, inspectors,
    configuration, transfers, reports, and oversight.
-   **OEM:** registers its devices, allocates stock, maintains devices,
    and handles repairs.
-   **Fitment Centre (FC):** installs and repairs devices.
-   **RTO Officer:** reviews and approves or rejects installations,
    reviews challans, and handles district-level operations.
-   **Inspector:** verifies fitment and drafts challans.
-   **Fleet Owner / School / Parent / Driver:** use the relevant fleet,
    school, child-transport, or duty features.

**Important:** State Admin access is constrained by the records and
permissions described in the guide. For example, a State Admin sees OEMs
created by themselves or their staff, and staff need matching
permissions to make changes.

## 2. State Admin's end-to-end operating model

At a high level, the State Admin's work follows this sequence:

1.  **Prepare platform master data** --- configure OEM device models,
    firmware, and SIM modules.
2.  **Configure state-wide rules** --- set device-offline and
    location-related thresholds and other settings.
3.  **Enable the device supply chain** --- OEMs register devices and
    allocate them to active fitment centres.
4.  **Oversee vehicle installation** --- fitment centres complete the
    eight-step installation and submit it to the appropriate RTO.
5.  **Oversee approval and compliance** --- RTO officers approve or
    reject installations; State Admin can inspect the state-wide picture
    and relevant reports.
6.  **Operate the state command centre** --- monitor vehicles, review
    alerts and SOS events, manage geofences/watchlists, and send
    permitted device commands.
7.  **Manage enforcement** --- create and transfer inspectors, review
    challans, and monitor automatically drafted silent-device challans.
8.  **Maintain ownership and records** --- process ownership transfers,
    merge eligible duplicate accounts, and untag devices where
    justified.
9.  **Support users and communicate changes** --- route support tickets
    and publish announcements.
10. **Review reports and audit history** --- monitor device health,
    installations, SIM validity, alerts, enforcement, ownership, and
    audit activity.

These are connected workflows, not one single wizard. Some steps depend
on another role completing an action.

------------------------------------------------------------------------

## 3. Sign-in, session handling, and permissions

### Sign-in flow

1.  The user enters an email address and password.
2.  The platform checks the account and role.
3.  The user is directed to the role's home page, unless they had
    requested a specific page before signing in, in which case the
    platform returns them to that page.

### Forced password change

A user must change their password before using the panel when: - it is
their first login with a password supplied by someone else; - an
administrator has requested a reset; or - the password is older than
**90 days**.

Until the change is complete, panel navigation redirects to **Change
Password**.

### Session and audit rules

-   **15 minutes** without mouse, keyboard, touch, or scroll activity
    causes automatic sign-out.
-   Activity in any open panel tab counts as activity.
-   Super Admin can inspect active sessions and terminate them.
-   Reuse of an old, already-used sign-in key causes all sessions for
    that user to be ended.
-   Sign-ins, failed refreshes, and forced sign-outs are written to the
    audit log.

### Role versus jurisdiction

Role determines which menus and actions are available. Jurisdiction
determines which vehicles and related records appear. A user may be able
to view a record but still be refused edit/delete actions. Menus not
available to a role are not shown.

------------------------------------------------------------------------

## 4. State Admin master data: OEM Management

**Purpose:** Define the device-related reference data that OEMs are
allowed to use. OEMs cannot create, edit, or delete this master data;
they can view their own device models and register devices against
configured models, firmware, and SIM modules.

### 4.1 Device Models

The State Admin selects an OEM and maintains the model record,
including: - model name and part number; - network profile and status; -
TAC number and issue date; - COP number and validity dates.

A device model already linked to devices cannot be deleted.

### 4.2 Firmware

Firmware records include: - OEM; - device model; - firmware version; -
release date; - update type; - status.

A firmware version cannot be moved to a different device model.

### 4.3 SIM Modules

SIM module records include: - OEM; - module name; - SIM manufacturer; -
primary and secondary operators; - primary and secondary SIM types; -
status.

A SIM module already linked to devices cannot be deleted.

### Important COP reminder distinction

The daily COP expiry reminder uses the COP validity recorded on the
OEM's own account, not the COP date stored on a device model. The guide
says the reminder is sent daily at **09:00**, once per expiry date. The
default reminder threshold is **30 days**.

### Dependencies and downstream impact

Incorrect or missing master data can prevent an OEM from registering a
device with the correct model, firmware, or SIM module. These records
are therefore upstream dependencies for device registration and
installation.

------------------------------------------------------------------------

## 5. System Configuration

**Purpose:** Control state-wide thresholds that affect other workflows.
Each setting can be switched on or off, and every change is recorded in
the audit log.

  -----------------------------------------------------------------------
  Setting                 Default / documented    Effect
                          status                  
  ----------------------- ----------------------- -----------------------
  Device offline alert    24 hours                Sets how long without
                                                  data before a
                                                  device-offline alert is
                                                  raised.

  COP expiry reminder     30 days                 Reminder lead time for
                                                  an OEM's COP
                                                  certificate.

  TAC expiry reminder     30 days; saved for      The guide identifies
                          future use              this as future-use
                                                  configuration.

  Fitment centre to       1 km                    Maximum proximity used
  vehicle distance                                during installation
                                                  step 2. Turning it off
                                                  disables this check.

  Inspector to vehicle    1 km                    Proximity used when an
  distance                                        inspector drafts a
                                                  challan. Turning it off
                                                  disables this check.

  RTO to vehicle distance 1 km; check off by      Radius for the RTO
                          default                 installation-approval
                                                  location check.

  RTO vehicle location    2 minutes               Required recency of
  freshness                                       vehicle position if the
                                                  RTO location check is
                                                  enabled.
  -----------------------------------------------------------------------

**RTO approval location caveat:** The location check is built but
temporarily switched off in the supplied guide. Until the approval
screen sends the officer's location and the setting is enabled, the
Approve action does not check where the vehicle or officer is. When
enabled, the check requires a fresh vehicle position and checks three
distances: vehicle to RTO office, officer to RTO office, and vehicle to
officer. The result is saved for audit.

Configuration changes can materially alter installation, challan, and
alert outcomes. They should be treated as operational changes rather
than cosmetic preferences.

------------------------------------------------------------------------

## 6. Device lifecycle: factory/stock to an approved vehicle

The core lifecycle spans State Admin, OEM, fitment centre, and RTO.

### Stage A --- State Admin prepares the reference data

The State Admin creates the device models, firmware versions, and SIM
modules under OEM Management.

### Stage B --- OEM registers devices

The OEM registers devices one by one or by Excel upload of up to
**10,000 devices**. Each row contains the IMEI, serial number, model,
SIM module, firmware, ICCID, primary and secondary mobile numbers, and
SIM validity date.

If rows fail validation, the OEM downloads a row-level Excel validation
report, fixes the errors, and uploads again.

### Stage C --- OEM allocates stock to a fitment centre

The OEM selects a district, chooses one of its active fitment centres,
selects available devices, and allocates them. Allocation history
records the date and receiver. Active devices still in allocated stock
can be rolled back to the OEM.

Device states are: - **Available:** in OEM stock and not allocated; -
**Allocated:** sent to a fitment centre, ready for installation; -
**Installed:** fitted to a vehicle; - **Faulty:** taken out of service
for repair.

Allocation rules: - an OEM can allocate only its own active, available
devices; - an allocated device or a device attached to an installation
cannot be allocated again; - a device that has passed Data Validation
and gone live cannot be allocated again; - only active devices still in
allocated stock can be rolled back; - a device not allocated to a
fitment centre cannot be installed.

### Stage D --- Fitment centre completes the eight-step installation

Installation progress is saved at each step, so the user can resume if
the browser closes.

1.  **Vehicle:** Search by registration or chassis number, choose owner
    type (individual, fleet owner, or school), and retrieve
    vehicle/owner details from VAHAN. A chassis number already linked to
    another registration is refused.
2.  **Device & SIM:** Select a device from the centre's stock. SIM
    validity must be at least two years for a vehicle under eight years
    old, or one year for an older vehicle. The device must be within the
    configured fitment-centre distance, default **1 km**, based on its
    recent GPS position.
3.  **Health:** Check device communication, external power, internal
    battery, and time sync. A healthy position packet must have arrived
    within the last **10 minutes**.
4.  **Panic:** Press the physical SOS button. The step passes only when
    the system receives the SOS signal from that device.
5.  **Documents:** Upload the RC, sale invoice, and fitment photographs.
    The files are stored with the installation and await verification.
6.  **Activation:** Review vehicle, owner, device, and SIM information
    and complete the checklist. All previous steps must be complete
    before activation.
7.  **Data Validation:** Run a **10-minute** watch window. The device
    should send about 60 packets; at least **80%** must arrive, and the
    last packet must arrive in the final 30 seconds. If it fails, retry
    starts a fresh 10-minute window.
8.  **Receipt:** Generate/download a PDF receipt with a QR code. The
    installation is submitted to the RTO.

Users can return to earlier steps until activation. After activation,
the earlier steps are locked because the device is live.

### Stage E --- RTO approves or rejects

1.  The installation appears in **Pending Approvals** for the RTO
    associated with the fitment centre that performed it.
2.  The RTO reviews vehicle/owner, device, SIM, installation,
    panic-test, fitment-centre, OEM, repair-history, and
    uploaded-document details.
3.  The RTO chooses **Approve** or **Reject**.
    -   **Approve:** the system checks that the installation and RTO
        belong to the same state.
    -   **Reject:** a remark is mandatory; the owner, OEM, and fitment
        centre are notified with the reason.
4.  Approved installations appear in **Approved Installations**.
    Rejected installations appear in **Rejected Installations** and must
    be corrected and resubmitted by the fitment centre.

### Stage F --- Live operation and service

Once the device passes Data Validation, the installation becomes active.
The device is permanently marked as used and cannot be fitted to another
vehicle or allocated again, even after repair or replacement.

-   **Repair of a live device:** it returns to the same vehicle after
    OEM repair and post-repair verification; it never returns to stock.
-   **Replacement of a live device:** a new device is fitted to the same
    vehicle; the old live device is retired from use on any other
    vehicle.
-   **Exception:** a device that failed before the installation became
    active may return to OEM Available stock after repair.
-   **Untag:** State Admin can detach a device from a vehicle for
    ownership transfer, OEM change, or admin correction. Untagged
    installations no longer count in tracking and remain listed in the
    Untagged Devices Report.

------------------------------------------------------------------------

## 7. Ownership transfer and account merge

### 7.1 Vehicle ownership transfer

The State Admin selects a vehicle, selects the new permit holder,
attaches supporting documents, and confirms.

Immediate effects: - the vehicle moves to the new owner and the old
owner loses access; - current driver assignment, active timetables,
scheduled duties, school mappings, geofence links, watchlist entries,
and vehicle-specific alert rules belonging to the old owner are
released; - past trips, alerts, and reports stay with the vehicle; - the
device remains fitted.

Transfers are permanent records. A mistake is corrected with another
transfer, not by editing the old one.

### 7.2 Account merge

The State Admin can merge eligible duplicate owner accounts. Every
vehicle from the source account transfers to the target using the
ownership-transfer rules.

The source account and its staff users are marked **Merged**. A merged
account: - holds no vehicles; - cannot be merged again; - cannot receive
transfers; - cannot have its status changed.

School accounts cannot be merged. Transfers and merges appear in the
Ownership Transfer Report and Account Merge Report.

------------------------------------------------------------------------

## 8. State-wide monitoring and operational response

### 8.1 Live Tracking

The State Admin can view every vehicle in the state. The screen contains
a vehicle list, coloured map markers, vehicle details, live track,
recent alerts, and pending alerts. Filters include RTO, OEM, fitment
centre, fleet owner/school, and status. The left panel has **Fleet** and
**Watchlist** tabs.

Vehicle status rules: - **Offline:** no packet received for more than 3
minutes, regardless of last speed; - **SOS:** latest packet carries the
emergency flag; - **Moving:** among the last three packets within three
minutes, at least one shows at least 5 km/h and the vehicle covered at
least 30 metres; - **Idle:** online but not moving according to the
moving rule.

### 8.2 GPS quality and historical packets

The platform flags GPS jumps, drift, weak signals, and no-fix positions.
Such points are retained for records but are not used to move the
live-map vehicle, calculate distance, evaluate geofences, or build
trips.

When network connectivity returns, stored history packets can fill gaps
in playback and reports. They do **not** move the live map or trigger
geofence entry/exit events because they represent past positions.

### 8.3 Alerts

Alerts can come from: - user-created rules (overspeed, excessive idling,
long parking, stationary device, offline, GPS unavailable, low internal
battery, ignition on/off); - geofences (entry, exit, no-parking); -
device emergencies (SOS, tamper, main battery disconnect).

A rule has a type, threshold, and scope. Scopes include all vehicles, an
RTO, a fitment centre, a vehicle, or a watchlist. For matching rules
belonging to the same user, the most specific rule wins in this order:
**vehicle → watchlist → fitment centre → RTO → all vehicles**. Rule
changes are recorded in Alert Set History.

A panel sees alerts from rules/geofences it created, plus every SOS in
its jurisdiction. Device-offline alerts are configured by the State
Admin and reach the State Admin and the vehicle's fleet-owner or school
account. Tamper and other device alarms are recorded and appear in
reports.

Repeated occurrences of one continuing problem are grouped as a single
incident. Repeats increase the count and update the last-occurrence
time. Once the problem ends, a later occurrence starts a new incident.

Alert workflow: 1. Alert is raised and remains **Open**. 2. An operator
takes it up and acknowledges it. 3. The alert is closed with a remark.
4. The system records who acted, when, the remark, and resolution time.

The Alerts page has **Active**, **Resolved**, and **Rules** tabs. Alerts
are grouped by vehicle and type, with a timeline of occurrences. **Close
all** closes every pending alert in the current group with one remark.

### 8.4 ERSS --- SOS emergency response

ERSS is specifically for SOS alerts. When a panic signal arrives: 1. The
SOS appears on ERSS with live location. 2. The system automatically
sends the device model's configured SOS-clear command. 3. The operator
acknowledges the event and contacts the nearest help centre. 4. The
operator closes the alert with a remark. 5. The full timeline is
retained.

**Clearing the device does not close the alert.** A human operator must
close it with a remark. Repeated SOS signals can cause the clear command
to be sent again. Automatic actions are recorded in the timeline as
performed by the system.

Help centres include police stations, hospitals, fire stations,
ambulances, and RTO offices. They can be added individually or in bulk;
bulk upload provides row-level results, upload history, and failed-row
download.

### 8.5 Geofences

The State Admin can draw a zone and configure entry, exit, optional
speed limit, and optional no-parking behavior. Vehicles can be added
individually, by group (RTO, OEM, fitment centre, fleet owner, school),
or as all vehicles in jurisdiction.

Rules: - entry/exit alerts are raised when a vehicle crosses a
boundary; - exit uses an approximately **20 m** margin to avoid repeated
boundary alerts; - no-parking alerts trigger when the vehicle is stopped
at **2 km/h or less** for longer than the configured duration; - a
duration of `0` means alert on entry; blank uses the **5-minute**
default; - moving off or leaving the zone resets the stop; - parking
violations are tied to no-parking geofences; ordinary ignition-off
parking is a long-parking rule alert; - only trusted live positions are
checked; - delete means archive, preserving past alerts/history;
activation/deactivation is a separate control.

State Admin and RTO can manage zones for vehicles in their jurisdiction;
fleet owners and schools can manage their own vehicles. A zone is
manageable by its creator or by a user whose jurisdiction includes every
vehicle in the zone.

### 8.6 Watchlists

Watchlists collect vehicles for closer monitoring. The State Admin can
see all watchlists in the state and add any vehicle. Other organisations
see and manage their own lists and can add only vehicles in their
jurisdiction.

A watchlist can have its own alert rules and geofence assignments.
Adding/removing a vehicle automatically updates the list's geofence
links. Each addition/removal is recorded with who and when under Watch
History.

### 8.7 Command Center

The OEM defines the command list for its device models, including
command labels and exact command text. One command can be marked **SOS
Clear** for automatic ERSS behavior.

An authorised user searches by vehicle number or IMEI, selects a
command, and sends it. Command status follows this lifecycle:

**Queued → Sent → Acknowledged** or **Failed**

Offline devices leave the command queued until they reconnect.
System-generated commands are labelled **System**. History can be
filtered by vehicle, status, owner/school, fitment centre, and date.

------------------------------------------------------------------------

## 9. Enforcement: inspectors and challans

### 9.1 Inspector management

The State Admin creates inspectors, assigns each to an RTO, and can
transfer them to another RTO.

Creation requires name, email, 10-digit contact number, city, optional
address, RTO, and a temporary password of at least 10 characters
containing uppercase, lowercase, and a number. Email and contact number
must be unique. The selected RTO must be active, in the State Admin's
state, and have an RTO officer account. The inspector must change the
temporary password on first login. Creation is audit-logged.

On transfer: - destination RTO must be active, in the same state, have
an RTO officer account, and differ from the current RTO; - the old link
is removed and the new link is created in one step; - the inspector
immediately works for the new RTO; - the audit log records old and new
RTO.

The RTO link controls which RTO's vehicles/reports the inspector can
access and where drafted challans are filed. An inspector without an
active RTO cannot draft a challan. **My Challans** always shows only
challans drafted by that inspector, including after transfer.

### 9.2 Challan workflow

1.  The inspector selects a vehicle and offence from the Challan Master
    and drafts a challan. The inspector's location is captured.
2.  If the vehicle device is sending data, the inspector must be within
    the configured distance (default **1 km**) of the vehicle's average
    position over the last five minutes; otherwise the draft is refused.
3.  The challan enters the RTO's work queue. RTO or State Admin reviews
    and approves it; a remark is optional.
4.  An approved challan is issued as either:
    -   **Paid:** amount must exactly equal the fine and a payment
        reference is required;
    -   **Cancelled:** a remark is required.
5.  The inspector can track their own challans under **My Challans**.

Only a drafted challan can be approved; only an approved challan can be
issued. RTOs see only challans in their area. Approvals and issuance are
audit-logged.

### 9.3 Automatic silent-device challan

Every **5 minutes**, the system checks active installations that have
sent no GPS data for **7 days** and automatically drafts a challan under
the "not sending data" offence. It still follows the same approval and
issuance process; it is not automatically issued.

------------------------------------------------------------------------

## 10. Public transport and school transport oversight

### 10.1 Public Information System (PIS)

The State Admin builds public transport schedules in dependent
layers: 1. **Stops** --- points on the map. 2. **Routes** --- ordered
stops, in up and down directions. 3. **Service calendar** --- service
days plus added/removed dates. 4. **Service pattern** --- stop-by-stop
timing. 5. **Timetables** --- departure times. 6. **Trips** --- each run
assigned to a vehicle.

The public **Track Public Transport** page lets citizens select a stop
or route and view timetable and live bus position without logging in.
Status messages may include "Arriving now," "Delayed data," or "This
trip has ended."

### 10.2 School, parent, and driver workflows

These panels are primarily owned by the school, but their data can be
relevant to State Admin fleet/school reporting and ownership changes.

School setup order: 1. Vehicles and Drivers, then Vehicle Driver
Mapping. 2. Stops and Routes. 3. Students and Parents. 4. Timetables
that combine vehicle, mapped driver, route, direction, weekdays, and
effective dates; students are assigned to a timetable. 5. Holidays and
Branches.

A student and parent are automatically linked when the student's
guardian email matches the parent's email, in either creation order, if
the student has no parent yet.

Attendance is marked per scheduled timetable as **Took Bus** or **Did
Not Take Bus**. Unmarked students remain **Unmarked**; the page warns
before discarding unsaved marks.

The parent panel shows children, attendance history, and school
holidays. Every minute, the system checks running school timetables and
sends an in-app notice when the bus is within **500 m** of a child's
stop, using a position no older than **10 minutes**. No notification is
sent on school holidays.

Drivers see today's duty, assigned vehicle, future duties, and duty
history. If vehicle ownership changes, scheduled duties are cancelled.

------------------------------------------------------------------------

## 11. SIM validity, repairs, and device maintenance

### 11.1 SIM validity extension

The OEM opens **SIM Validity Extension**, enters an IMEI, fetches the
device, selects a new validity date, and confirms. This is allowed only
for the OEM's own device installed on a vehicle with exactly one active
installation and an active SIM still assigned to the device.

The new date must be later than the current date and no more than: - two
years from today for a vehicle under eight years old; - one year from
today for an older vehicle.

Every extension is audit-logged with old and new dates. After device
registration, SIM validity cannot be changed through another route.

### 11.2 Repair and replacement

The fitment centre locates the current installation by vehicle number
and raises a repair with evidence photos (JPG/PNG, up to 5 MB). The OEM
records findings and chooses **Complete Repair** or **Mark Replacement
Required**. Only a device currently under repair can be marked for
replacement.

Replacement requires a reason and evidence (PDF/JPG/PNG, up to 5 MB).
The replacement device must be different and fitted to the same vehicle.
It repeats the required health, panic, document, activation, and
validation steps. Post-repair photos and checks are required before
repair completion. Repair receipts include a QR code that can be checked
on the public portal.

------------------------------------------------------------------------

## 12. Reports and auditability

Reports are filtered to the user's jurisdiction. Most can be exported.

  -----------------------------------------------------------------------
  Report family           Examples                Availability described
                                                  in the guide
  ----------------------- ----------------------- -----------------------
  Device                  Device Packets, Device  All tracking panels
                          Status & Connectivity,  
                          Device Health, SIM      
                          Validity, User Devices  

  Alerts                  Alert Report, Vehicle   All tracking panels
                          Alert Trail, Alert Set  
                          History                 

  Installation &          Installation            State Admin, RTO,
  maintenance             Performance,            Inspector, OEM, Fitment
                          Installation Report,    Centre, subject to each
                          Repair & Replacement,   report's stated scope
                          Fitment Centre Pulse,   
                          Expired SIM Report      
                          (OEM), six RTO          
                          installation reports    

  Compliance              Multiple-Challan        State Admin and Fleet
                          Vehicles, Driver        Owner
                          Compliance, Route       
                          Compliance, Permit      
                          Compliance, Driver      
                          Mapping, Challan Report 

  Fleet & school          Fleet Activity,         State Admin and School
                          Transport Schedules,    
                          Transport Students,     
                          Attendance,             
                          Driver--Vehicle History 

  Audit & ownership       Ownership Transfers,    State Admin, RTO, Super
                          Account Merges,         Admin, subject to
                          Untagged Devices, Watch report scope
                          History, Approval       
                          History, Audit          
  -----------------------------------------------------------------------

Key report behavior: - **Device Status & Connectivity:** classifies
devices as online, offline, intermittent, or not installed using last
packet and daily activity. - **Device Health:** shows battery/GPS
condition and seven-day counts of GPS jumps and weak signals. - **SIM
Validity:** under seven days is critical; under 30 days is at risk. A
SIM-expiry alert is raised three days before expiry. - **Device
Packets:** up to 31 days per search and 200 rows per page. Broad
searches without an IMEI may be refused and require narrowing. - **Alert
Report:** includes alerts from the user's own rules/geofences plus
SOS. - **Installation Report:** each installation is bucketed by
priority in this order: rejected by RTO, failed, successful, pending. -
**RTO installation reports:** filtered by the RTO of the fitment centre,
not the vehicle's registration RTO. Exports include all pages. -
**Untagged Devices Report:** retains old untagged records even if the
vehicle or device is later removed.

Audit history is important for traceability: system configuration
changes, sign-in/session events, inspector creation/transfers, ownership
transfers/merges, alert changes/closures, installation approval
decisions, challan approval/issue, and other listed actions are recorded
where the guide specifies.

------------------------------------------------------------------------

## 13. Helpdesk and announcements

### Helpdesk tickets

A ticket can be raised from a panel or public portal. The reporter can
choose to route it directly to the OEM; otherwise, the State Admin
assigns it. The documented flow is:

**Opened → Assigned → In_progress → Completed → Closed**

Every assignment and status change records the time and person.

### Announcements

The State Admin publishes announcements to selected user types: OEMs,
fitment centres, RTOs, inspectors, fleets, schools, or everyone.

Each announcement has: - importance: information, warning, or
critical; - start and end times; - optional PDF; - active/inactive
control.

The system updates status every minute: **scheduled** before start,
**active** during the time window, and **expired** after end. A
switched-off announcement remains inactive.

------------------------------------------------------------------------

## 14. Public portal and externally visible workflows

The public portal does not require login for the listed services:

-   **Find a fitment centre:** searches active centres with approved
    accounts and approved OEMs.
-   **Verify installation (QR):** displays whether an installation is
    genuine, its status, and activation status; invalid/expired links
    are identified.
-   **Verify repair receipt (QR):** displays vehicle, installation-time
    device snapshot, and current repair status.
-   **Support Center:** creates a ticket with description, 10-digit
    contact number, and optional attachment; tracks it by ticket code.
    Codes are remembered in the browser.
-   **Track Public Transport:** exposes live bus position and timetable.
-   **What's new:** displays release notes.

**Not connected yet according to the guide:** Installation Booking (slot
availability) and Download Receipt (mobile number + OTP) pages are
visible/designed but are not connected to the live system.

------------------------------------------------------------------------

## 15. Automatic jobs the State Admin should understand

  -----------------------------------------------------------------------
  Job                     Frequency               Behavior
  ----------------------- ----------------------- -----------------------
  GPS quality check       Every packet            Flags jumps, drift,
                                                  weak/no-fix positions
                                                  and excludes them from
                                                  live map, distance,
                                                  geofences, and trips.

  Alert/geofence checks   Every packet            Evaluates rules and
                                                  zones and groups
                                                  incidents.

  SOS clear               On every SOS            Sends device-model
                                                  SOS-clear command;
                                                  alert remains open for
                                                  operator closure.

  Device offline check    Continuously            Raises offline alerts
                                                  according to State
                                                  Admin configuration.

  Silent-device challan   Every 5 minutes         Drafts challans for
                                                  active installations
                                                  without GPS data for
                                                  seven days.

  SIM expiry alert        Every 5 minutes         Raises alert when a SIM
                                                  expires within three
                                                  days.

  Parent bus-near-stop    Every minute            Sends notice when bus
  notice                                          is within 500 m of the
                                                  child's stop, with
                                                  sufficiently fresh
                                                  position.

  Announcement status     Every minute            Updates scheduled →
                                                  active → expired.

  COP expiry reminder     Daily at 09:00          Notifies OEM once per
                                                  expiry date, using the
                                                  OEM account's COP
                                                  validity.

  Daily summaries         Daily                   Produces distance,
                                                  activity, and
                                                  GPS-quality totals for
                                                  reports.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 16. Operational numbers worth remembering

  -----------------------------------------------------------------------
  Item                                Value
  ----------------------------------- -----------------------------------
  Device packet interval              About 10 seconds

  Vehicle Offline status              No packet for more than 3 minutes

  Moving status                       At least 5 km/h and 30 m covered
                                      within the last 3 minutes

  Automatic sign-out                  15 minutes idle

  Password expiry                     90 days

  Minimum SIM validity at             2 years if vehicle is under 8 years
  installation                        old; 1 year if older

  Health packet freshness             Within 10 minutes

  Data Validation                     10-minute window; at least 80% of
                                      expected packets

  Fitment/inspector distance          1 km by default

  RTO approval position freshness     2 minutes; location check currently
                                      off

  No-parking default                  Stopped at 2 km/h or less for 5
                                      minutes

  Geofence exit margin                About 20 m

  Device-offline alert default        24 hours

  Silent-device challan threshold     No GPS data for 7 days

  SIM critical / at risk              Under 7 days / under 30 days

  Parent bus-stop notification        Within 500 m

  Device Packets search               Up to 31 days and 200 rows per page

  Repair evidence photo               JPG/PNG, up to 5 MB

  Replacement evidence                PDF/JPG/PNG, up to 5 MB

  Driver bulk upload                  Up to 500 rows

  OEM device bulk upload              Up to 10,000 devices
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 17. Practical State Admin mental model

When investigating an issue, follow the dependency chain rather than
starting with the visible symptom:

-   **Device cannot be registered:** check OEM master data (model,
    firmware, SIM module), device ownership by OEM, and upload
    validation.
-   **Device cannot be allocated:** check OEM ownership, active status,
    stock state, and whether it has ever gone live.
-   **Installation cannot proceed:** check device allocation to the FC,
    vehicle/chassis mapping, SIM validity, proximity, recent healthy
    packet, physical SOS, documents, and prior-step completion.
-   **Installation is not live:** check Data Validation packet count,
    the 80% threshold, and the final-30-second packet condition.
-   **Installation is waiting for approval:** check the RTO associated
    with the fitment centre and the Pending Approvals queue.
-   **Vehicle looks incorrectly positioned:** inspect GPS-quality flags
    and distinguish live packets from stored history packets.
-   **Expected alert is missing:** check the rule/geofence owner, scope,
    most-specific-rule precedence, vehicle jurisdiction, live-position
    quality, and incident state.
-   **SOS remains open after clear:** this is expected; the operator
    must close it with a remark.
-   **Challan was not drafted:** check inspector's active RTO, vehicle
    scope, offence selection, and configured location check.
-   **Vehicle is visible to the wrong owner after a transfer:** verify
    the transfer record and released owner-specific assignments; history
    should remain with the vehicle.
-   **SIM or device may be failing:** review Device Health, Device
    Status & Connectivity, SIM Validity, packet history, and
    repair/replacement history.
-   **A record appears deleted:** determine whether the feature archives
    the record (geofences do) and whether historical reports preserve
    it.

## 18. Scope notes and limitations

This explanation reflects the supplied guide, not an independent
verification of the live application. The guide describes user-visible
behavior and does not specify implementation details, API contracts,
database design, or every permission combination.

Two explicit status caveats should not be overlooked: 1. The RTO
approval location check is built but currently switched off. 2.
Installation Booking and Download Receipt pages are visible but not
connected to the live system.

Where the guide does not define a rule, this document does not invent
one. Confirm any behavior not covered here against the current
application requirements or product owner before treating it as an
acceptance criterion.
