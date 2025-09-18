#! /usr/bin/env python3

import os
from collections import Counter
from datetime import datetime
from typing import Generator
from zoneinfo import ZoneInfo

import click
import requests

REGISTRATIONS_URL = "https://api.tito.io/v3/{account}/{event}/registrations"
ACTIVITIES_URL = "https://api.tito.io/v3/{account}/{event}/activities"

NON_WORKSHOP_ACTIVITIES = (
    "Conference Day 1",
    "Conference Day 2",
    "Conference Day 3",
    "Conference Dinner",
    "Geochicas",
    "Icebreaker",
    "T-Shirt",
    "Women in Geospatial Breakfast",
    "B2B",
)

GROUPED = {
    "Conference Day 1": "Conference and Icebreaker",
    "Conference Day 2": "Conference and Icebreaker",
    "Conference Day 3": "Conference and Icebreaker",
    "Icebreaker": "Conference and Icebreaker",
}


def get_tito_tickets(
    tito_key: str, account: str, event: str
) -> Generator[dict, dict, dict]:
    """
    Get a list of tickets from Tito
    """
    url = REGISTRATIONS_URL.format(account=account, event=event)

    headers = {"Authorization": f"Token token={tito_key}"}

    next_page = 1
    while next_page is not None:
        parameters = {"page": next_page}
        response = requests.get(url, headers=headers, params=parameters)

        response.raise_for_status()
        registrations = response.json()
        next_page = registrations["meta"]["next_page"]

        for registration in registrations["registrations"]:
            for ticket in registration["quantities"].values():
                yield ticket


def summarise_tickets(tickets: dict) -> dict:
    """
    Take a list of registrations and summarise them by ticket type
    """
    summary = Counter()

    for ticket in tickets:
        summary.update({ticket["release"]: int(ticket["quantity"])})

    return summary


def get_tito_activities(
    tito_key: str, account: str, event: str
) -> Generator[dict, dict, dict]:
    """
    Get a list of activities from Tito in a summarised form
    """
    url = ACTIVITIES_URL.format(account=account, event=event)

    headers = {"Authorization": f"Token token={tito_key}"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    activities = response.json()

    summary = {
        "Workshops": 0,
    }
    non_workshop_names = set()
    for activity in activities["activities"]:
        if activity["name"] in NON_WORKSHOP_ACTIVITIES:
            if activity["name"] in GROUPED:
                grouped_name = GROUPED[activity["name"]]
                if grouped_name in summary:
                    summary[grouped_name] += activity["allocation_count"]
                else:
                    summary[grouped_name] = activity["allocation_count"]
            else:
                summary[activity["name"]] = activity["allocation_count"]
                non_workshop_names.add(activity["name"])
        else:
            summary["Workshops"] += activity["allocation_count"]

    print('Non-workshop activities found:', ', '.join(sorted(non_workshop_names)))

    return summary


def post_to_slack(
    webhook: str, summary: dict, event_date: datetime, timezone: str, dry_run: bool=False
) -> None:
    """
    Post a message to Slack

    Parameters:
    webhook (str): The Slack webhook URL
    summary (dict): A dictionary of ticket types and quantities
    event_date (datetime): The date of the event
    timezone (str): The timezone of the event (like "Australia/Hobart")
    """
    today = datetime.now(tz=ZoneInfo(timezone))
    days_to_go = (event_date - today).days

    message = (
        f"It's {today.strftime('%B %-d')}, "
        f"there are {days_to_go} days until the conference and "
        "here's the latest registration numbers:\n"
    )
    message += "\n".join(
        [
            f"\t• {ticket_type}: {quantity}"
            for ticket_type, quantity in summary.items()
        ]
    )
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
            }
        ]
    }

    if dry_run:
        print("Dry run, not posting to Slack")
        print(message)
    else:
        print("Posting to Slack")
        print(message)
        response = requests.post(webhook, json=payload)
        if response.status_code != 200:
            print(f"Error posting to Slack: {response.text}")
        response.raise_for_status()


# A CLI function that takes in a tito organisation and event and posts to Slack
@click.command("tito-to-slack")
@click.argument("account", type=str)
@click.argument("event", type=str)
@click.argument("event-date", type=str)
@click.option("--summary-type", type=str, default="registrations")
@click.option("--dry-run", is_flag=True, default=False)
def cli(account, event, event_date, summary_type, dry_run):
    TITO_KEY = os.environ.get("TITO_KEY")

    if TITO_KEY is None:
        raise ValueError("TITO_KEY not set")

    slack_webhook = os.environ.get("SLACK_WEBHOOK")
    if slack_webhook is None:
        raise ValueError("Environment variable SLACK_WEBHOOK not set")

    timezone = os.environ.get("TIMEZONE", "Australia/Hobart")

    try:
        year, month, day = [int(x) for x in event_date.split("-")]
        event_date = datetime(year, month, day, tzinfo=ZoneInfo(timezone))
    except ValueError:
        raise ValueError("EVENT_DATE must be in the format YYYY-MM-DD")

    if summary_type not in ["registrations", "activities"]:
        raise ValueError("Invalid summary type")
    
    if summary_type == "registrations":
        regos = get_tito_tickets(TITO_KEY, account, event)

        if regos is None:
            raise ValueError("No tickets returned")

        summary = summarise_tickets(regos)
    elif summary_type == "activities":
        summary = get_tito_activities(TITO_KEY, account, event)

        if summary is None:
            raise ValueError("No activities returned")


    post_to_slack(slack_webhook, summary, event_date, timezone, dry_run)


if __name__ == "__main__":
    cli()
