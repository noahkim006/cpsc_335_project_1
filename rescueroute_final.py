import csv, os
from pathlib import Path
from contextlib import nullcontext
from collections import deque

donations_by_id = {}
recipients_by_id = {}
volunteers_by_id = {}

processed_donor_ids = set()
processed_recipient_ids = set()
processed_volunteer_ids = set()

invalid_donations = []

fifo_assignments = []
fifo_rejected = []

greedy_assignments = []
greedy_rejected = []


## following can be used as a framework for other validation tests
def valid_time(time):
    try:
        hour, minutes = map(int, time.split(":"))
        return 0 <= hour <= 23 and 0 <= minutes <= 59
    except (ValueError, TypeError, AttributeError):
        return False

def create_assignment(
        donation_id,
        recipient_id,
        volunteer_id,
        scheduled_time,
        decision_reason,
        status
):
    return {
        "donation_id": donation_id,
        "recipient_id": recipient_id,
        "volunteer_id": volunteer_id,
        "scheduled_time": scheduled_time,
        "decision_reason": decision_reason,
        "status": status
    }

def time_to_minutes(time):
    hours, minutes = map(int, time.split(":"))
    return hours * 60 + minutes

def read_rows(filename, required_fields):
    """Read normalized rows; malformed donation rows remain in the audit."""
    path = Path(__file__).resolve().parent / "assets" / filename
    try:
        with path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames:
                return  # Empty input is a valid empty dataset.
            if not set(required_fields) <= set(reader.fieldnames):
                raise ValueError(f"{filename}: missing required columns")
            for line, row in enumerate(reader, 2):
                if None in row or any(row.get(key) is None for key in required_fields):
                    print(f"{filename}, row {line}: malformed CSV row skipped")
                    if filename == "donations.csv":
                        invalid_donations.append({"donation_id": f"row-{line}",
                                                  "quantity": 0,
                                                  "reason": "Malformed CSV row; quantity unknown."})
                    continue
                yield {key: (value or "").strip() for key, value in row.items()}
    except (OSError, csv.Error) as error:
        raise ValueError(f"Cannot load {path}: {error}") from error


def load_files():
    # Load donation information into dictionary -- O(n)
    with nullcontext(read_rows('donations.csv', ['donation_id', 'donor_name', 'food_type', 'quantity', 'pickup_area', 'ready_time', 'expiry_time'])) as csv_reader:

        for row in csv_reader:
            if not row:
                print(
                    "File cannot be empty"
                )
                break

            donation_id = row["donation_id"]
            if donation_id and donation_id in processed_donor_ids:
                print(f"Duplicate donation {donation_id} skipped")
                continue
            if donation_id:
                processed_donor_ids.add(donation_id)
            try:
                audit_quantity = max(0, int(row["quantity"]))
            except (ValueError, TypeError):
                audit_quantity = 0
            audit = {"donation_id": donation_id or "(missing ID)",
                     "quantity": audit_quantity,
                     "reason": "Invalid required field, quantity, or time; see validation message."}
            invalid_donations.append(audit)
            if not row["donor_name"] or not row["pickup_area"]:
                audit["reason"] = "Missing donor name or pickup area."
                print(f"Invalid donor name or pickup area for {donation_id}")
                continue

            ##Validation of donation ID
            if not donation_id:
                audit["reason"] = "Donation ID is missing."
                print(
                    "\n---------------------------------------------\n"
                    "Donation ID cannot be empty\n"
                    "\n---------------------------------------------\n"
                )
                continue

            ## Validate quantity
            try:
                quantity = int(row["quantity"])
                if quantity <= 0:
                    audit["reason"] = "Quantity must be positive."
                    print(
                        "\n---------------------------------------------\n"
                        f"Invalid quantity for donation {donation_id}\n"
                        "\n---------------------------------------------\n"
                    )
                    continue
            except (ValueError, TypeError, AttributeError):
                audit["reason"] = "Quantity must be an integer."
                print(
                    "\n---------------------------------------------\n"
                    f"Invalid quantity for donation {donation_id}\n"
                    "\n---------------------------------------------\n"
                )
                continue

            ##Validate food type
            if not row["food_type"].strip():
                audit["reason"] = "Food type is missing."
                print(
                    "\n---------------------------------------------\n"
                    f"Invalid food type for donation {donation_id}\n"
                    "\n---------------------------------------------\n"
                )
                continue

            ##Validate times
            if not valid_time(row["ready_time"]) or not valid_time(row["expiry_time"]):
                audit["reason"] = "Invalid ready or expiry time."
                print(
                    "\n---------------------------------------------\n"
                    f"Invalid time format for donation {donation_id}\n"
                    "\n---------------------------------------------\n"
                )
                continue


            ready_time_in_minutes = time_to_minutes(row["ready_time"])
            expiry_time_in_minutes = time_to_minutes(row["expiry_time"])

            # Reject an invalid same-day window; retain its quantity in the audit. 
            if (expiry_time_in_minutes - ready_time_in_minutes) <= 0:
                audit["reason"] = "Expiry must be later than ready time (same-day model)."
                print(
                    "\n---------------------------------------------\n"
                    f"{donation_id} has an invalid same-day ready/expiry window\n"
                    f"{donation_id} will not be added to the data set\n"
                    "\n---------------------------------------------\n"
                )
                continue
            invalid_donations.remove(audit)

            donations_by_id[donation_id] = {
                "donor_name": row["donor_name"],
                "food_type": row["food_type"],
                "quantity": quantity,
                "pickup_area": row["pickup_area"],
                "ready_time": row["ready_time"],
                "expiry_time": row["expiry_time"],
                "remaining_shelf_life": (expiry_time_in_minutes - ready_time_in_minutes)
            }
            # print(
            #     f"{donation_id} ready hour: {ready_hour}  --- ready minutes: {ready_minutes}\n"
            #     f"expiry hour: {expiry_hour} -- expiry minutes: {expiry_minutes}\n"
            #     f"Remaining shelf life: {donations_by_id[donation_id]["remaining_shelf_life"] / 60}"
            #     "\n-------------------------------------------------------------------\n"
            # )

        # Load recipient information into another dictionary -- O(n)
    with nullcontext(read_rows('recipients.csv', ['recipient_id', 'org_name', 'accepted_food_types', 'capacity', 'area', 'closing_time'])) as csv_reader:

        for row in csv_reader:
            if not row: 
                print("File cannot be empty")
                break

            recipient_id = row["recipient_id"]
            if not recipient_id:
                print("Recipient ID cannot be empty")
                continue

            # Skip entry if already in the set (unique data struct)
            if recipient_id in processed_recipient_ids:
                print(
                    "\n---------------------------------------------\n"
                    f"{recipient_id} already exists in the set\n"
                    f"{recipient_id} cannot be added to the set"
                    "\n---------------------------------------------\n"
                )
                continue

            # Validate organization name
            if not row["org_name"].strip():
                print(f"Invalid organization name for recipient {recipient_id}")
                continue

            # Validate food types
            if not any(part.strip() for part in row["accepted_food_types"].split(";")):
                print(f"Invalid food types for recipient {recipient_id}")
                continue

            ## Validate capacity
            try:
                capacity = int(row["capacity"])
                if capacity <= 0:
                    print(f"Invalid capacity for recipient {recipient_id}")
                    continue
            except (ValueError, TypeError):
                print(f"Invalid capacity for recipient {recipient_id}")
                continue

            ##Validate area
            if not row["area"].strip():
                print(f"Invalid area for recipient {recipient_id}")
                continue

            ##Validate closing time
            if not valid_time(row["closing_time"].strip()):
                print(f"Invalid closing time for recipient {recipient_id}")
                continue


            processed_recipient_ids.add(recipient_id)

            recipients_by_id[recipient_id] = {
                "org_name": row["org_name"],
                "accepted_food_types": ";".join(part.strip() for part in row["accepted_food_types"].split(";") if part.strip()),
                "capacity": capacity,
                "area": row["area"],
                "closing_time": row["closing_time"]
            }


## Load volunteer information into a third dictionary
    with nullcontext(read_rows('volunteers.csv', ['volunteer_id', 'vehicle_capacity', 'area', 'available_from', 'available_until', 'max_pickups'])) as csv_reader:

        for row in csv_reader:
            if not row:
                print("File cannot be empty")
                break

            volunteer_id = row["volunteer_id"]

            ## Validate volunteer ID
            if not volunteer_id:
                print("Volunteer ID cannot be empty")
                continue

            ## Skip duplicate volunteer
            if volunteer_id in processed_volunteer_ids:
                print(
                    "\n---------------------------------------------\n"
                    f"{volunteer_id} already exists in the set\n"
                    f"{volunteer_id} cannot be added to the set"
                    "\n---------------------------------------------\n"
                )
                continue

            ##Validate vehicle capacity
            try:
                vehicle_capacity = int(row["vehicle_capacity"])
                if vehicle_capacity <= 0:
                    print(f"Invalid vehicle capacity for volunteer {volunteer_id}")
                    continue
            except (ValueError, TypeError):
                print(f"Invalid vehicle capacity for volunteer {volunteer_id}")
                continue

            ## Validate area
            if not row["area"]:
                print(f"Invalid area for volunteer {volunteer_id}")
                continue

            ## Validate availabilty times
            if not valid_time(row["available_from"].strip()):
                print(f"Invalid available from time for volunteer {volunteer_id}")
                continue

            if not valid_time(row["available_until"].strip()):
                print(f"Invalid available until time for volunteer {volunteer_id}")
                continue

            if time_to_minutes(row["available_until"]) < time_to_minutes(row["available_from"]):
                print(f"Invalid availability window for volunteer {volunteer_id}")
                continue

            ##Validate maximum pickups
            try:
                max_pickups = int(row["max_pickups"])
                if max_pickups <= 0:
                    print(f"Invalid maximum pickups for volunteer {volunteer_id}")
                    continue
            except (ValueError, TypeError):
                print(f"Invalid maximum pickups for volunteer {volunteer_id}")
                continue

            processed_volunteer_ids.add(volunteer_id)

            volunteers_by_id[volunteer_id] = {
                "vehicle_capacity": vehicle_capacity,
                "area": row["area"],
                "available_from": row["available_from"],
                "available_until": row["available_until"],
                "max_pickups": max_pickups
            }


# Earliest expiry first; ties: smaller quantity, earlier ready time, then CSV order. 
def sort_by_remaining_shelf_life(donations):
    return sorted(
        donations.items(), 
        key = lambda donation:(
            time_to_minutes(donation[1]["expiry_time"]),
            donation[1]["quantity"],
            time_to_minutes(donation[1]["ready_time"])
        )
    )
# FIFO preserves CSV arrival order, independently of ready time. 
def sort_by_arrival_time(donations):
    return list(donations.items())  # CSV insertion order is arrival order.

def fifo_implementation(sorted_donations_by_arrival_time):
    fifo_assignments.clear()
    fifo_rejected.clear()

    #Track remaining resources seperately for each implementation of FIFO/greedy
    remaining_recipient_capacity = {
        recipient_id: recipient["capacity"]
        for recipient_id, recipient in recipients_by_id.items()
    }
    remaining_volunteer_pickups = {
        volunteer_id: volunteer["max_pickups"]
        for volunteer_id, volunteer in volunteers_by_id.items()
    }

    for donation_id, donation in sorted_donations_by_arrival_time:
        possible_volunteer_id, possible_recipient_id, possible_pickup_time = None, None, None
        for recipient_id, recipient in recipients_by_id.items():
            recipient_accepted_food_types = recipient["accepted_food_types"].split(";")
            if(
                donation["pickup_area"] != recipient["area"]
                or donation["food_type"] not in recipient_accepted_food_types
                or donation["quantity"] > remaining_recipient_capacity[recipient_id]
            ):
                continue

            for volunteer_id, volunteer in volunteers_by_id.items():
                pickup_time = max(time_to_minutes(donation["ready_time"]), time_to_minutes(volunteer["available_from"]))

                if (
                    donation["quantity"] <= volunteer["vehicle_capacity"]
                    and donation["pickup_area"] == volunteer["area"]
                    and remaining_volunteer_pickups[volunteer_id] > 0
                    and pickup_time <= time_to_minutes(volunteer["available_until"])
                    and pickup_time < time_to_minutes(donation["expiry_time"])
                    and pickup_time <= time_to_minutes(recipient["closing_time"])
                ):
                    possible_recipient_id = recipient_id
                    possible_volunteer_id = volunteer_id
                    possible_pickup_time = pickup_time
                    break

            if possible_volunteer_id is not None:
                break

        if possible_volunteer_id is not None and possible_recipient_id is not None:
            scheduled_time = (
                f"{possible_pickup_time // 60:02d}:"
                f"{possible_pickup_time % 60:02d}"
            )

            fifo_assignments.append(
                create_assignment(
                    donation_id,
                    possible_recipient_id,
                    possible_volunteer_id,
                    scheduled_time,
                    assignment_reason(donation, possible_recipient_id, possible_volunteer_id, scheduled_time),
                    "assigned"
                )
            )
            remaining_recipient_capacity[possible_recipient_id] -= donation["quantity"]
            remaining_volunteer_pickups[possible_volunteer_id] -= 1
        else:

            fifo_rejected.append(
                create_assignment(
                    donation_id,
                    None,
                    None,
                    None,
                    rejection_reason(donation, remaining_recipient_capacity, remaining_volunteer_pickups),
                    "unassigned"
                )
            )


def greedy_implementation(sorted_doonations_by_shelf_life):
    greedy_assignments.clear()
    greedy_rejected.clear()
    #Track remaining resources seperately for each implementation of FIFO/greedy
    remaining_recipient_capacity = {
        recipient_id: recipient["capacity"]
        for recipient_id, recipient in recipients_by_id.items()
    }
    remaining_volunteer_pickups = {
        volunteer_id: volunteer["max_pickups"]
        for volunteer_id, volunteer in volunteers_by_id.items()
    }

    for donation_id, donation in sorted_doonations_by_shelf_life:
        possible_volunteer_id, possible_recipient_id, possible_pickup_time = None, None, None

        # Same constraint rules as FIFO since the greedy implementation can be seen in our sorting method, which prioritizes 
        # donations by earliest expiry (with documented tie-breakers)
        for recipient_id, recipient in recipients_by_id.items():
            recipient_accepted_food_types = recipient["accepted_food_types"].split(";")
            if(
                donation["pickup_area"] != recipient["area"]
                or donation["food_type"] not in recipient_accepted_food_types
                or donation["quantity"] > remaining_recipient_capacity[recipient_id]
            ):
                continue

            for volunteer_id, volunteer in volunteers_by_id.items():
                pickup_time = max(time_to_minutes(donation["ready_time"]), time_to_minutes(volunteer["available_from"]))

                if (
                    donation["quantity"] <= volunteer["vehicle_capacity"]
                    and donation["pickup_area"] == volunteer["area"]
                    and remaining_volunteer_pickups[volunteer_id] > 0
                    and pickup_time <= time_to_minutes(volunteer["available_until"])
                    and pickup_time < time_to_minutes(donation["expiry_time"])
                    and pickup_time <= time_to_minutes(recipient["closing_time"])
                ):
                    possible_recipient_id = recipient_id
                    possible_volunteer_id = volunteer_id
                    possible_pickup_time = pickup_time
                    break

            if possible_volunteer_id is not None:
                break

        if possible_volunteer_id is not None:
            scheduled_time = (
                f"{possible_pickup_time // 60:02d}:"
                f"{possible_pickup_time % 60:02d}"
            )

            reason = assignment_reason(donation, possible_recipient_id,
                                       possible_volunteer_id, scheduled_time)

            greedy_assignments.append(
                create_assignment(
                    donation_id,
                    possible_recipient_id,
                    possible_volunteer_id,
                    scheduled_time,
                    reason,
                    "assigned"
                )
            )

            remaining_recipient_capacity[possible_recipient_id] -= donation["quantity"]
            remaining_volunteer_pickups[possible_volunteer_id] -= 1
        else:
            greedy_rejected.append(
                create_assignment(
                    donation_id,
                    None,
                    None,
                    None,
                    rejection_reason(donation, remaining_recipient_capacity, remaining_volunteer_pickups),
                    "unassigned"
                )
            )


def assignment_reason(donation, recipient_id, volunteer_id, scheduled_time):
    recipient = recipients_by_id[recipient_id]
    volunteer = volunteers_by_id[volunteer_id]
    return (
        f"Assigned to {recipient['org_name']} with {volunteer_id} at {scheduled_time}: "
        f"{donation['quantity']} units fit recipient and vehicle capacity "
        f"({volunteer['vehicle_capacity']} units); food type and area match, "
        f"pickup is within availability and closing time, and precedes expiry "
        f"at {donation['expiry_time']}."
    )


def rejection_reason(donation, capacities, pickups):
    """Describe the first feasibility stage with no remaining candidates."""
    recipients = [(rid, r) for rid, r in recipients_by_id.items()
                  if r['area'] == donation['pickup_area']
                  and donation['food_type'] in r['accepted_food_types'].split(';')]
    if not recipients:
        return "Unassigned: no recipient in the pickup area accepts this food type."
    recipients = [(rid, r) for rid, r in recipients
                  if capacities[rid] >= donation['quantity']]
    if not recipients:
        return "Unassigned: compatible recipients lack remaining capacity."
    volunteers = [(vid, v) for vid, v in volunteers_by_id.items()
                  if v['area'] == donation['pickup_area']
                  and v['vehicle_capacity'] >= donation['quantity']]
    if not volunteers:
        return "Unassigned: no volunteer in the pickup area has enough vehicle capacity."
    volunteers = [(vid, v) for vid, v in volunteers if pickups[vid] > 0]
    if not volunteers:
        return "Unassigned: suitable volunteers have reached their maximum pickups."
    available = [(vid, v, max(time_to_minutes(donation['ready_time']),
                             time_to_minutes(v['available_from'])))
                 for vid, v in volunteers]
    available = [(vid, v, time) for vid, v, time in available
                 if time <= time_to_minutes(v['available_until'])]
    if not available:
        return "Unassigned: suitable volunteers are unavailable after the food is ready."
    available = [(vid, v, time) for vid, v, time in available
                 if time < time_to_minutes(donation['expiry_time'])]
    if not available:
        return "Unassigned: suitable volunteers cannot pick up before expiry."
    return "Unassigned: compatible recipients close before a suitable volunteer can pick up."


def calculate_metrics(assignments, rejected):
    # Urgent = earliest-expiring quarter, rounded up, including cutoff ties.
    ordered = sorted(donations_by_id,
                     key=lambda did: time_to_minutes(donations_by_id[did]['expiry_time']))
    urgent = set()
    if ordered:
        cutoff = time_to_minutes(donations_by_id[ordered[(len(ordered) - 1) // 4]]['expiry_time'])
        urgent = {did for did in ordered
                  if time_to_minutes(donations_by_id[did]['expiry_time']) <= cutoff}
    assigned_ids = {a['donation_id'] for a in assignments}
    rescued = sum(donations_by_id[did]['quantity'] for did in assigned_ids)
    total_quantity = (sum(d['quantity'] for d in donations_by_id.values())
                      + sum(d['quantity'] for d in invalid_donations))
    recipient_capacity = sum(r['capacity'] for r in recipients_by_id.values())
    # Total potential transport capacity across all allowed pickup slots.
    volunteer_capacity = sum(v['vehicle_capacity'] * v['max_pickups']
                             for v in volunteers_by_id.values())
    return {
        'Donations received': len(donations_by_id) + len(invalid_donations),
        'Donations assigned': len(assignments),
        'Donations unassigned': len(rejected) + len(invalid_donations),
        'Food quantity rescued': rescued,
        'Food quantity at risk': total_quantity - rescued,
        'Urgent rescue rate (%)': 100 * len(urgent & assigned_ids) / len(urgent) if urgent else 0,
        'Recipient utilization (%)': 100 * rescued / recipient_capacity if recipient_capacity else 0,
        'Volunteer utilization (%)': 100 * rescued / volunteer_capacity if volunteer_capacity else 0,
    }


def print_results(name, ordered, assignments, rejected):
    print(f"\n{name}")
    outcomes = {a['donation_id']: a for a in assignments + rejected}
    previous = None
    for donation_id, donation in ordered:
        if name == 'Greedy' and previous is not None:
            print(f"Priority: {donation_id} follows {previous}: earliest expiry first; "
                  "ties use smaller quantity, earlier ready time, then CSV order.")
        print(f"{donation_id}: {outcomes[donation_id]['decision_reason']}")
        previous = donation_id
    for invalid in invalid_donations:
        print(f"{invalid['donation_id']}: Unassigned: {invalid['reason']}")


def main():
    for collection in (donations_by_id, recipients_by_id, volunteers_by_id,
                       processed_donor_ids, processed_recipient_ids,
                       processed_volunteer_ids, invalid_donations):
        collection.clear()
    try:
        load_files()
    except ValueError as error:
        print(f"Input error: {error}")
        return 1
    fifo_order = deque(sort_by_arrival_time(donations_by_id))
    greedy_order = sort_by_remaining_shelf_life(donations_by_id)
    fifo_implementation(fifo_order)
    greedy_implementation(greedy_order)
    print_results('FIFO', fifo_order, fifo_assignments, fifo_rejected)
    print_results('Greedy', greedy_order, greedy_assignments, greedy_rejected)
    fifo_metrics = calculate_metrics(fifo_assignments, fifo_rejected)
    greedy_metrics = calculate_metrics(greedy_assignments, greedy_rejected)
    print('\nComparison (percentage differences are percentage points)')
    print(f"{'Metric':<30} {'FIFO':>10} {'Greedy':>10} {'Greedy-FIFO':>12}")
    for metric, value in fifo_metrics.items():
        other = greedy_metrics[metric]
        print(f"{metric:<30} {value:>10.2f} {other:>10.2f} {other-value:>+12.2f}")
    print('Urgent group: earliest-expiring quarter of valid donations, including cutoff ties.')
    print('Invalid donation rows count as unassigned; duplicates are excluded. '
          'Unknown or nonpositive quantities contribute zero to quantity totals.')
    print('Volunteer utilization uses vehicle capacity times maximum pickups across all volunteers.')
    print('Simulation: one day; CSV order is arrival order; pickup/delivery duration is zero. '
          'No current-clock expiry check or real route scheduling is modeled.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
