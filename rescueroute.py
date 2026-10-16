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


## following can be used as a framework for other validation tests
def valid_time(time):
    try:
        hour, minutes = map(int, time.split(":"))
        return 0 <= hour <= 23 and 0 <= minutes <= 59
    except ValueError:
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

def load_files():
    # Load donation information into dictionary -- O(n)
    with open('assets/donations.csv', "r") as donation_file:

        if os.path.getsize('assets/donations.csv') == 0:
            print("Donations file contains no data")
            quit()

        csv_reader = csv.DictReader(donation_file)

        for row in csv_reader:
            if not row:
                print(
                    "File cannot be empty"
                )
                break

            donation_id = row["donation_id"]

            ##Validation of donation ID
            if not donation_id:
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
                    print(
                        "\n---------------------------------------------\n"
                        f"Invalid quantity for donation {donation_id}\n"
                        "\n---------------------------------------------\n"
                    )
                    continue
            except ValueError:
                print(
                    "\n---------------------------------------------\n"
                    f"Invalid quantity for donation {donation_id}\n"
                    "\n---------------------------------------------\n"
                )
                continue

            ##Validate food type
            if not row["food_type"].strip():
                print(
                    "\n---------------------------------------------\n"
                    f"Invalid food type for donation {donation_id}\n"
                    "\n---------------------------------------------\n"
                )
                continue

            ##Validate times
            if not valid_time(row["ready_time"]) or not valid_time(row["expiry_time"]):
                print(
                    "\n---------------------------------------------\n"
                    f"Invalid time format for donation {donation_id}\n"
                    "\n---------------------------------------------\n"
                )
                continue


            ready_time_in_minutes = time_to_minutes(row["ready_time"])
            expiry_time_in_minutes = time_to_minutes(row["expiry_time"])

            # Skip entry if donation item has already expired 
            if (expiry_time_in_minutes - ready_time_in_minutes) <= 0:
                print(
                    "\n---------------------------------------------\n"
                    f"{donation_id} has already expired and is not suitable for human consumption\n"
                    f"{donation_id} will not be added to the data set\n"
                    "\n---------------------------------------------\n"
                )
                continue
            # Skip entry if already in the set (unique data struct)
            if donation_id in processed_donor_ids:
                print(
                    "\n---------------------------------------------\n"
                    f"{donation_id} already exists in the set\n"
                    f"{donation_id} cannot be added to the data set"
                    "\n---------------------------------------------\n"
                )
                continue

            processed_donor_ids.add(donation_id)


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
    with open('assets/recipients.csv', 'r') as recipients_file:
        if os.path.getsize('assets/recipients.csv') == 0:
            print("Recipients file contains no data")
            quit()

        csv_reader = csv.DictReader(recipients_file)
        for row in csv_reader:
            if not row: 
                print("File cannot be empty")
                break

            recipient_id = row["recipient_id"]

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
            if not row["accepted_food_types"].strip():
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
                "accepted_food_types": row["accepted_food_types"],
                "capacity": capacity,
                "area": row["area"],
                "closing_time": row["closing_time"]
            }


## Load volunteer information into a third dictionary
    with open('assets/volunteers.csv', 'r') as volunteers_file:
        if os.path.getsize('assets/volunteers.csv') == 0:
            print("Volunteers file contains no data")
            quit()

        csv_reader = csv.DictReader(volunteers_file)
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


# To use for greedy implementations -- Sort donations by remaining shelf life - in case of a tie, 
def sort_by_remaining_shelf_life(donations):
    return sorted(
        donations.items(), 
        key = lambda donation:(
            donation[1]["remaining_shelf_life"],
            donation[1]["quantity"],
            time_to_minutes(donation[1]["ready_time"])
        )
    )
# To use for FIFO implementation -- Sort by donations that arrived first to last 
def sort_by_arrival_time(donations):
    return sorted(donations.items(), key = lambda donation:(donation[1]["ready_time"]))

def fifo_implementation(sorted_donations_by_arrival_time):

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
        # Check feasability of recipients and volunteers
        for volunteer_id, volunteer in volunteers_by_id.items():
            # Set the pickup time for donations as the latest time between donation ready time and 
            # volunteer availability time since volunteer cant pick up food unless its ready
            pickup_time = max(time_to_minutes(donation["ready_time"]), time_to_minutes(volunteer["available_from"]))
            # Constraint check to see if volunteer meets all needed criteria to pick up the donation
            if (
                donation["quantity"] <= volunteer["vehicle_capacity"]
                and donation["pickup_area"] == volunteer["area"]
                and remaining_volunteer_pickups[volunteer_id] > 0
                and pickup_time <= time_to_minutes(volunteer["available_until"])
                and pickup_time <= time_to_minutes(donation["expiry_time"])
            ):
                for recipient_id, recipient in recipients_by_id.items():
                    recipient_accepted_food_types = recipient["accepted_food_types"].split(";")
                    if (
                        (donation["pickup_area"] == recipient["area"])
                        and (donation["food_type"] in recipient_accepted_food_types)
                        and (donation["quantity"] <= remaining_recipient_capacity[recipient_id])
                        and (pickup_time <= time_to_minutes(recipient["closing_time"]))
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

            print(
                "----------------------------------------------------------------\n"
                f"Volunteer {possible_volunteer_id} with "
                f"{volunteers_by_id[possible_volunteer_id]['vehicle_capacity']} "
                f"space was able to pick up donation {donation_id} "
                f"(size: {donation['quantity']}) and deliver it to "
                f"{recipients_by_id[possible_recipient_id]['org_name']}\n"
                "----------------------------------------------------------------\n"
            )

            fifo_assignments.append(
                create_assignment(
                    donation_id,
                    possible_recipient_id,
                    possible_volunteer_id,
                    scheduled_time,
                    "Assigned: all matching constraints were satisfied.",
                    "assigned"
                )
            )
            remaining_recipient_capacity[possible_recipient_id] -= donation["quantity"]
            remaining_volunteer_pickups[possible_volunteer_id] -= 1
        else:
            print(f"{donation_id} was rejected\n")

            fifo_rejected.append(
                create_assignment(
                    donation_id,
                    None,
                    None,
                    None,
                    "Unassigned: no feasible recipient-volunteer pair was found.",
                    "unassigned"
                )
            )


def greedy_implementation(sorted_doonations_by_shelf_life):
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
        # donations with remaining shelf life
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

            reason = (
                "Assigned by urgency-first order: food type, area, capacity, "
                "volunteer availability, expiry, and recipient closing-time "
                "constraints were satisfied."
            )

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
                    "Unassigned: no feasible recipient-volunteer pair was found.",
                    "unassigned"
                )
            )


load_files()

sorted_by_shelf_life = sort_by_remaining_shelf_life(donations_by_id)
sorted_by_arrival_time = deque(sort_by_arrival_time(donations_by_id))

fifo_implementation(sorted_by_arrival_time)
greedy_implementation(sorted_by_shelf_life)

print(greedy_assignments)
print("\n\n\n\n\n")
print(greedy_rejected)