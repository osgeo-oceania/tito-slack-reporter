#! /usr/bin/env python3

import datetime
import os
from collections import Counter

import click
import requests

REGISTRATIONS_URL = "https://api.tito.io/v3/{account}/{event}/registrations"
EVENT_DATE = datetime.datetime(2023, 10, 16)


def get_tito_tickets(tito_key: str, account: str, event: str) -> dict:
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


def post_to_slack(webhook: str, registrations: dict) -> None:
    """
    Post a message to Slack
    """
    today = datetime.datetime.now()
    days_to_go = (EVENT_DATE - today).days

    message = (
        f"It's {today.strftime('%B %-d')}, "
        f"there are {days_to_go} days until the conference and "
        "here's the latest registration numbers:\n"
    )
    message += "\n".join(
        [
            f"\t• {ticket_type}: {quantity}"
            for ticket_type, quantity in registrations.items()
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

    response = requests.post(webhook, json=payload)

    response.raise_for_status()


# A CLI function that takes in a tito organisation and event and posts to Slack
@click.command("tito-to-slack")
@click.argument("account", type=str)
@click.argument("event", type=str)
def cli(account, event):
    TITO_KEY = os.environ.get("TITO_KEY")

    if TITO_KEY is None:
        raise ValueError("TITO_KEY not set")

    SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK")

    if SLACK_WEBHOOK is None:
        raise ValueError("SLACK_WEBHOOK not set")

    tickets = get_tito_tickets(TITO_KEY, account, event)

    if tickets is None:
        raise ValueError("No tickets returned")

    summarised = summarise_tickets(tickets)
    post_to_slack(SLACK_WEBHOOK, summarised)


if __name__ == "__main__":
    cli()
