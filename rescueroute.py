import csv, os
from collections import deque

donations_by_id = {}
recipients_by_id = {}
volunteers_by_id = {}

processed_donor_ids = set()
processed_recipient_ids = set()
processed_volunteer_ids = set()

assignments = []

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

            ## Skipping duplication donation IDs
            if donation_id in processed_donor_ids:
                print(
                    "\n---------------------------------------------\n"
                    f"{donation_id} already exists in the set\n"
                    f"{donation_id} cannot be added to the data set"
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

            ready_hour, ready_minutes = map(int, row["ready_time"].split(":"))
            expiry_hour, expiry_minutes = map(int, row["expiry_time"].split(":"))

            ready_time_in_seconds = (ready_minutes * 60) + (ready_hour * 3600)
            expiry_time_in_seconds = (expiry_minutes * 60) + (expiry_hour * 3600)


            
            # Skip entry if already in the set (unique data struct)
            
            if donation_id in processed_donor_ids:
                print(
                    "\n---------------------------------------------\n"
                    f"{donation_id} already exists in the set\n"
                    f"{donation_id} cannot be added to the data set"
                    "\n---------------------------------------------\n"
                )
                continue
            # Skip entry if donation item has already expired 
            if (expiry_time_in_seconds - ready_time_in_seconds) <= 0:
                print(
                    "\n---------------------------------------------\n"
                    f"{donation_id} has already expired and is not suitable for human consumption\n"
                    f"{donation_id} will not be added to the data set\n"
                    "\n---------------------------------------------\n"
                )
            # Skip 

            processed_donor_ids.add(donation_id)


            donations_by_id[donation_id] = {
                "donor_name": row["donor_name"],
                "food_type": row["food_type"],
                "quantity": row["quantity"],
                "pickup_area": row["pickup_area"],
                "ready_time": row["ready_time"],
                "expiry_time": row["expiry_time"],
                "remaining_shelf_life": (expiry_time_in_seconds - ready_time_in_seconds)
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
                "capacity": row["capacity"],
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
                "vehicle_capacity": row["vehicle_capacity"],
                "area": row["area"],
                "available_from": row["available_from"],
                "available_until": row["available_until"],
                "max_pickups": row["max_pickups"]
            }


# To use for greedy implementations -- Sort donations by remaining shelf life - in case of a tie, 
def sort_by_remaining_shelf_life(donations):
    return sorted(donations.values(), key = lambda donation:(
        donation["remaining_shelf_life"],
        -int(donation["quantity"]))
    )
    # x = sorted(donations.values(), key=lambda donation:(
    #         donation["remaining_shelf_life"],
    #         -int(donation["quantity"]))
    #     )
    # for i in x: 
    #     print(
    #         f"{i["donor_name"]} --- Remaining Shelf Life: {i["remaining_shelf_life"] / 60} minutes --- Quantity: {i["quantity"]} -- Ready Time: {i["ready_time"]}\n"
    #         "-----------------------------------------------------------\n"
    #     )

# To use for FIFO implementation -- Sort by donations that arrived first to last 
def sort_by_arrival_time(donations):
    return sorted(donations.values(), key = lambda donation:(donation["ready_time"]))
    # x = deque(sorted(donations.values(), key = lambda donation:donation["ready_time"]))
    # for i in x: 
    #     print(
    #         f"{i["donor_name"]} --- Remaining Shelf Life: {i["remaining_shelf_life"] / 60} minutes --- Quantity: {i["quantity"]} -- Ready Time: {i["ready_time"]}\n"
    #         "-----------------------------------------------------------\n"
    #     )


# for id, obj in donations_by_id.items():
#     print(id, obj, "\n")

# for id, obj in recipients_by_id.items():
#     print(id, obj, "\n")

load_files()

sorted_by_shelf_life = sort_by_remaining_shelf_life(donations_by_id)
sorted_by_arrival_time = deque(sort_by_arrival_time(donations_by_id))