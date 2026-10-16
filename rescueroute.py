import csv, os
from collections import deque

donations_by_id = {}
recipients_by_id = {}
volunteers_by_id = {}

processed_donor_ids = set()
processed_recipient_ids = set()
processed_volunteer_ids = set()

fifo_assignments = []
fifo_rejected = []

greedy_assignments = []
greedy_rejected = []


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


def valid_columns(csv_reader, required_columns, filename):
    if not csv_reader.fieldnames:
        print(f"{filename} is empty or missing its header.")
        return False

    for column in required_columns:
        if column not in csv_reader.fieldnames:
            print(f"{filename} is missing required column: {column}")
            return False

    return True


def load_files():
    donation_columns = [
        "donation_id", "donor_name", "food_type", "quantity",
        "pickup_area", "ready_time", "expiry_time"
    ]

    recipient_columns = [
        "recipient_id", "org_name", "accepted_food_types",
        "capacity", "area", "closing_time"
    ]

    volunteer_columns = [
        "volunteer_id", "vehicle_capacity", "area",
        "available_from", "available_until", "max_pickups"
    ]

    for filename in [
        "assets/donations.csv",
        "assets/recipients.csv",
        "assets/volunteers.csv"
    ]:
        if not os.path.exists(filename):
            print(f"File not found: {filename}")
            return False

        if os.path.getsize(filename) == 0:
            print(f"{filename} contains no data.")
            return False

    with open("assets/donations.csv", "r", newline="") as donation_file:
        csv_reader = csv.DictReader(donation_file)

        if not valid_columns(csv_reader, donation_columns, "Donations file"):
            return False

        for row in csv_reader:
            if not row or any(row.get(column) is None for column in donation_columns):
                print("Donation row is missing required fields.")
                continue

            donation_id = row["donation_id"].strip()

            if not donation_id:
                print("Donation ID cannot be empty.")
                continue

            if donation_id in processed_donor_ids:
                print(f"{donation_id} already exists and cannot be added again.")
                continue

            try:
                quantity = int(row["quantity"])
                if quantity <= 0:
                    print(f"Invalid quantity for donation {donation_id}.")
                    continue
            except (ValueError, TypeError):
                print(f"Invalid quantity for donation {donation_id}.")
                continue

            food_type = row["food_type"].strip()
            pickup_area = row["pickup_area"].strip()
            ready_time = row["ready_time"].strip()
            expiry_time = row["expiry_time"].strip()

            if not food_type:
                print(f"Invalid food type for donation {donation_id}.")
                continue

            if not pickup_area:
                print(f"Invalid pickup area for donation {donation_id}.")
                continue

            if not valid_time(ready_time) or not valid_time(expiry_time):
                print(f"Invalid time format for donation {donation_id}.")
                continue

            ready_minutes = time_to_minutes(ready_time)
            expiry_minutes = time_to_minutes(expiry_time)

            if expiry_minutes <= ready_minutes:
                print(
                    f"{donation_id} has already expired or has an invalid "
                    "expiry time and will not be added."
                )
                continue

            processed_donor_ids.add(donation_id)

            donations_by_id[donation_id] = {
                "donor_name": row["donor_name"].strip(),
                "food_type": food_type,
                "quantity": quantity,
                "pickup_area": pickup_area,
                "ready_time": ready_time,
                "expiry_time": expiry_time,
                "remaining_shelf_life": expiry_minutes - ready_minutes
            }

    with open("assets/recipients.csv", "r", newline="") as recipients_file:
        csv_reader = csv.DictReader(recipients_file)

        if not valid_columns(csv_reader, recipient_columns, "Recipients file"):
            return False

        for row in csv_reader:
            if not row or any(row.get(column) is None for column in recipient_columns):
                print("Recipient row is missing required fields.")
                continue

            recipient_id = row["recipient_id"].strip()

            if not recipient_id:
                print("Recipient ID cannot be empty.")
                continue

            if recipient_id in processed_recipient_ids:
                print(f"{recipient_id} already exists and cannot be added again.")
                continue

            org_name = row["org_name"].strip()
            accepted_food_types = [
                food.strip()
                for food in row["accepted_food_types"].split(";")
                if food.strip()
            ]
            area = row["area"].strip()
            closing_time = row["closing_time"].strip()

            if not org_name:
                print(f"Invalid organization name for recipient {recipient_id}.")
                continue

            if not accepted_food_types:
                print(f"Invalid accepted food types for recipient {recipient_id}.")
                continue

            try:
                capacity = int(row["capacity"])
                if capacity <= 0:
                    print(f"Invalid capacity for recipient {recipient_id}.")
                    continue
            except (ValueError, TypeError):
                print(f"Invalid capacity for recipient {recipient_id}.")
                continue

            if not area:
                print(f"Invalid area for recipient {recipient_id}.")
                continue

            if not valid_time(closing_time):
                print(f"Invalid closing time for recipient {recipient_id}.")
                continue

            processed_recipient_ids.add(recipient_id)

            recipients_by_id[recipient_id] = {
                "org_name": org_name,
                "accepted_food_types": ";".join(accepted_food_types),
                "capacity": capacity,
                "area": area,
                "closing_time": closing_time
            }

    with open("assets/volunteers.csv", "r", newline="") as volunteers_file:
        csv_reader = csv.DictReader(volunteers_file)

        if not valid_columns(csv_reader, volunteer_columns, "Volunteers file"):
            return False

        for row in csv_reader:
            if not row or any(row.get(column) is None for column in volunteer_columns):
                print("Volunteer row is missing required fields.")
                continue

            volunteer_id = row["volunteer_id"].strip()

            if not volunteer_id:
                print("Volunteer ID cannot be empty.")
                continue

            if volunteer_id in processed_volunteer_ids:
                print(f"{volunteer_id} already exists and cannot be added again.")
                continue

            try:
                vehicle_capacity = int(row["vehicle_capacity"])
                if vehicle_capacity <= 0:
                    print(f"Invalid vehicle capacity for volunteer {volunteer_id}.")
                    continue
            except (ValueError, TypeError):
                print(f"Invalid vehicle capacity for volunteer {volunteer_id}.")
                continue

            area = row["area"].strip()
            available_from = row["available_from"].strip()
            available_until = row["available_until"].strip()

            if not area:
                print(f"Invalid area for volunteer {volunteer_id}.")
                continue

            if not valid_time(available_from):
                print(f"Invalid available-from time for volunteer {volunteer_id}.")
                continue

            if not valid_time(available_until):
                print(f"Invalid available-until time for volunteer {volunteer_id}.")
                continue

            if time_to_minutes(available_until) < time_to_minutes(available_from):
                print(f"Invalid availability range for volunteer {volunteer_id}.")
                continue

            try:
                max_pickups = int(row["max_pickups"])
                if max_pickups <= 0:
                    print(f"Invalid maximum pickups for volunteer {volunteer_id}.")
                    continue
            except (ValueError, TypeError):
                print(f"Invalid maximum pickups for volunteer {volunteer_id}.")
                continue

            processed_volunteer_ids.add(volunteer_id)

            volunteers_by_id[volunteer_id] = {
                "vehicle_capacity": vehicle_capacity,
                "area": area,
                "available_from": available_from,
                "available_until": available_until,
                "max_pickups": max_pickups
            }

    return True


def sort_by_remaining_shelf_life(donations):
    return sorted(
        donations.items(),
        key=lambda donation: (
            donation[1]["remaining_shelf_life"],
            donation[1]["quantity"],
            time_to_minutes(donation[1]["ready_time"])
        )
    )


def sort_by_arrival_time(donations):
    return sorted(
        donations.items(),
        key=lambda donation: donation[1]["ready_time"]
    )


def assignment_reason(donation, recipient_id, volunteer_id, scheduled_time):
    recipient = recipients_by_id[recipient_id]
    volunteer = volunteers_by_id[volunteer_id]

    return (
        f"Assigned to {recipient['org_name']} ({recipient_id}) at "
        f"{scheduled_time} with volunteer {volunteer_id}. "
        f"The recipient accepts {donation['food_type']}, the pickup areas "
        f"match, and the quantity of {donation['quantity']} fits the "
        f"remaining recipient capacity and the volunteer's vehicle capacity "
        f"of {volunteer['vehicle_capacity']}. The pickup is within the "
        f"volunteer's availability and before the donation expiry and "
        f"recipient closing time."
    )


def rejection_reason(donation, remaining_recipient_capacity, remaining_volunteer_pickups):
    compatible_recipient = False
    recipient_with_capacity = False
    compatible_volunteer = False
    sufficient_vehicle_capacity = False
    available_volunteer = False

    for recipient_id, recipient in recipients_by_id.items():
        accepted_food_types = [
            food.strip()
            for food in recipient["accepted_food_types"].split(";")
        ]

        if (
            donation["pickup_area"] != recipient["area"]
            or donation["food_type"] not in accepted_food_types
        ):
            continue

        compatible_recipient = True

        if donation["quantity"] > remaining_recipient_capacity[recipient_id]:
            continue

        recipient_with_capacity = True

        for volunteer_id, volunteer in volunteers_by_id.items():
            if (
                donation["pickup_area"] != volunteer["area"]
                or remaining_volunteer_pickups[volunteer_id] <= 0
            ):
                continue

            if donation["quantity"] > volunteer["vehicle_capacity"]:
                continue

            sufficient_vehicle_capacity = True

            pickup_time = max(
                time_to_minutes(donation["ready_time"]),
                time_to_minutes(volunteer["available_from"])
            )

            if (
                pickup_time <= time_to_minutes(volunteer["available_until"])
                and pickup_time <= time_to_minutes(donation["expiry_time"])
                and pickup_time <= time_to_minutes(recipient["closing_time"])
            ):
                compatible_volunteer = True
                available_volunteer = True
                break

        if compatible_volunteer:
            break

    if not compatible_recipient:
        return (
            "Unassigned: no recipient matches both the donation's food type "
            "and pickup area."
        )

    if not recipient_with_capacity:
        return (
            "Unassigned: compatible recipients exist, but none has enough "
            "remaining capacity for the entire donation."
        )

    if not sufficient_vehicle_capacity:
        return (
            "Unassigned: no eligible volunteer has enough vehicle capacity "
            "for the entire donation."
        )

    if not available_volunteer:
        return (
            "Unassigned: no feasible volunteer-recipient pair was found. "
            "Volunteer pickup limits, availability, donation expiry, or "
            "recipient closing times may prevent the pickup."
        )

    return "Unassigned: no feasible recipient-volunteer pair was found."


def fifo_implementation(sorted_donations_by_arrival_time):
    remaining_recipient_capacity = {
        recipient_id: recipient["capacity"]
        for recipient_id, recipient in recipients_by_id.items()
    }

    remaining_volunteer_pickups = {
        volunteer_id: volunteer["max_pickups"]
        for volunteer_id, volunteer in volunteers_by_id.items()
    }

    for donation_id, donation in sorted_donations_by_arrival_time:
        possible_volunteer_id = None
        possible_recipient_id = None
        possible_pickup_time = None

        for volunteer_id, volunteer in volunteers_by_id.items():
            pickup_time = max(
                time_to_minutes(donation["ready_time"]),
                time_to_minutes(volunteer["available_from"])
            )

            if (
                donation["quantity"] <= volunteer["vehicle_capacity"]
                and donation["pickup_area"] == volunteer["area"]
                and remaining_volunteer_pickups[volunteer_id] > 0
                and pickup_time <= time_to_minutes(volunteer["available_until"])
                and pickup_time <= time_to_minutes(donation["expiry_time"])
            ):
                for recipient_id, recipient in recipients_by_id.items():
                    accepted_food_types = [
                        food.strip()
                        for food in recipient["accepted_food_types"].split(";")
                    ]

                    if (
                        donation["pickup_area"] == recipient["area"]
                        and donation["food_type"] in accepted_food_types
                        and donation["quantity"] <= remaining_recipient_capacity[recipient_id]
                        and pickup_time <= time_to_minutes(recipient["closing_time"])
                    ):
                        possible_recipient_id = recipient_id
                        possible_volunteer_id = volunteer_id
                        possible_pickup_time = pickup_time
                        break

                if possible_recipient_id is not None:
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
                    assignment_reason(
                        donation,
                        possible_recipient_id,
                        possible_volunteer_id,
                        scheduled_time
                    ),
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
                    rejection_reason(
                        donation,
                        remaining_recipient_capacity,
                        remaining_volunteer_pickups
                    ),
                    "unassigned"
                )
            )


def greedy_implementation(sorted_donations_by_shelf_life):
    remaining_recipient_capacity = {
        recipient_id: recipient["capacity"]
        for recipient_id, recipient in recipients_by_id.items()
    }

    remaining_volunteer_pickups = {
        volunteer_id: volunteer["max_pickups"]
        for volunteer_id, volunteer in volunteers_by_id.items()
    }

    for donation_id, donation in sorted_donations_by_shelf_life:
        possible_volunteer_id = None
        possible_recipient_id = None
        possible_pickup_time = None

        for recipient_id, recipient in recipients_by_id.items():
            accepted_food_types = [
                food.strip()
                for food in recipient["accepted_food_types"].split(";")
            ]

            if (
                donation["pickup_area"] != recipient["area"]
                or donation["food_type"] not in accepted_food_types
                or donation["quantity"] > remaining_recipient_capacity[recipient_id]
            ):
                continue

            for volunteer_id, volunteer in volunteers_by_id.items():
                pickup_time = max(
                    time_to_minutes(donation["ready_time"]),
                    time_to_minutes(volunteer["available_from"])
                )

                if (
                    donation["quantity"] <= volunteer["vehicle_capacity"]
                    and donation["pickup_area"] == volunteer["area"]
                    and remaining_volunteer_pickups[volunteer_id] > 0
                    and pickup_time <= time_to_minutes(volunteer["available_until"])
                    and pickup_time <= time_to_minutes(donation["expiry_time"])
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

            greedy_assignments.append(
                create_assignment(
                    donation_id,
                    possible_recipient_id,
                    possible_volunteer_id,
                    scheduled_time,
                    assignment_reason(
                        donation,
                        possible_recipient_id,
                        possible_volunteer_id,
                        scheduled_time
                    ),
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
                    rejection_reason(
                        donation,
                        remaining_recipient_capacity,
                        remaining_volunteer_pickups
                    ),
                    "unassigned"
                )
            )


def print_results(title, assignments, rejected):
    print("\n")
    print("=================================================================")
    print(title)
    print("=================================================================")


    number = 1
    for assignment in assignments:
        donation = donations_by_id[assignment["donation_id"]]

        print(
            f"\n{number}. {assignment['donation_id']} - "
            f"{donation['donor_name']} "
            f"({donation['quantity']} units of {donation['food_type']})"
        )
        print(f"   ASSIGNED at {assignment['scheduled_time']}")
        print(
            f"   Recipient: {recipients_by_id[assignment['recipient_id']]['org_name']} "
            f"({assignment['recipient_id']})"
        )
        print(f"   Volunteer: {assignment['volunteer_id']}")
        print(f"   Why: {assignment['decision_reason']}")
        number += 1

    for assignment in rejected:
        donation = donations_by_id[assignment["donation_id"]]

        print(
            f"\n{number}. {assignment['donation_id']} - "
            f"{donation['donor_name']} "
            f"({donation['quantity']} units of {donation['food_type']})"
        )
        print("   UNASSIGNED.")
        print(f"   Why: {assignment['decision_reason']}")
        number +=1

    print(f"\nTotal assigned: {len(assignments)}")
    print(f"Total unassigned: {len(rejected)}")
    print(f"Total donations processed: {len(assignments) + len(rejected)}")


load_files()

sorted_by_shelf_life = sort_by_remaining_shelf_life(donations_by_id)
sorted_by_arrival_time = deque(sort_by_arrival_time(donations_by_id))

fifo_implementation(sorted_by_arrival_time)
greedy_implementation(sorted_by_shelf_life)

print_results("FIFO RESULTS", fifo_assignments, fifo_rejected)
print_results("GREEDY RESULTS", greedy_assignments, greedy_rejected)