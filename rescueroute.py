import csv
from collections import deque

donations_by_id = {}
recipients_by_id = {}


# Load donation information into dictionary
with open('assets/donations.csv', "r") as donation_file:
    csv_reader = csv.DictReader(donation_file)
    for row in csv_reader:
        donation_id = row["donation_id"]

        donations_by_id[donation_id] = {
            "donor_name": row["donor_name"],
            "food_type": row["food_type"],
            "quantity": row["quantity"],
            "pickup_area": row["pickup_area"],
            "ready_time": row["ready_time"],
            "expiry_time": row["expiry_time"]
        }

# Load recipient information into another dictionary
with open('assets/recipients.csv', 'r') as recipients_file:
    csv_reader = csv.DictReader(recipients_file)
    for row in csv_reader:
        recipient_id = row["recipient_id"]

        recipients_by_id[recipient_id] = {
            "org_name": row["org_name"],
            "accepted_food_types": row["accepted_food_types"],
            "capacity": row["capacity"],
            "area": row["area"],
            "closing_time": row["closing_time"]
        }


