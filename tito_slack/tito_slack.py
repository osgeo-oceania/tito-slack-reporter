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
    "Business to Business",
    "TGP Breakfast",
    "Auckland Transport HOP card",
)

GROUPED = {
    "Conference Day 1": "Conference and Icebreaker",
    "Conference Day 2": "Conference and Icebreaker",
    "Conference Day 3": "Conference and Icebreaker",
    "Icebreaker": "Conference and Icebreaker",
    # Monday morning
    "Advanced PostGIS: Beyond the basics Workshop": "Workshops (Monday morning)",
    "Building Geospatial AI Applications: From Data to Insights with Open Source Tools Workshop": "Workshops (Monday morning)",
    "Build the Thing: A Hands-On Product Workshop for Geospatial Makers Workshop": "Workshops (Monday morning)",
    "Cloud-Native Geospatial for Earth Observation Workshop": "Workshops (Monday morning)",
    "Diving into pygeoapi Workshop": "Workshops (Monday morning)",
    "Exploring the ZOO-Project-DRU and OGC Application Package Workshop": "Workshops (Monday morning)",
    "Hands-on DGGS and OGC DGGS-API with DGGRID and pydggsapi Workshop": "Workshops (Monday morning)",
    "Introduction to GeoServer Workshop": "Workshops (Monday morning)",
    "Let’s create Interactive Web Maps with the Open-Source WebGIS: Re:Earth Visualizer + Re:Earth CMS Workshop": "Workshops (Monday morning)",
    "QField & QFieldCloud: Hands-On Fieldwork Workshop": "Workshops (Monday morning)",
    # Monday afternoon
    "Cartography for Rebels: Building Beautiful Maps with Free Tools Workshop": "Workshops (Monday afternoon)",
    "Doing Geospatial with Python Workshop": "Workshops (Monday afternoon)",
    "Exploring Cloud-Native Geospatial Formats: Hands-on with Raster Data Workshop": "Workshops (Monday afternoon)",
    "GeoTools Geospatial Introduction Workshop": "Workshops (Monday afternoon)",
    "Getting Sentinel Data within Seconds with STAC Workshop": "Workshops (Monday afternoon)",
    "International QField Day Workshop": "Workshops (Monday afternoon)",
    "Scalable Remote Sensing Workflows with Xarray Workshop": "Workshops (Monday afternoon)",
    "QGIS Graphical Modeler: Build Smarter Workflows with Algorithms and Expressions Workshop": "Workshops (Monday afternoon)",
    "QGIS Plugin Development": "Workshops (Monday afternoon)",
    "Tile serving with MapLibre/Martin/Planetiler - base and overlays Workshop": "Workshops (Monday afternoon)",
    # Tuesday morning
    "Cloud-based Remote Sensing with QGIS and Google Earth Engine Workshop": "Workshops (Tuesday morning)",
    "Exploring Cloud-Native Geospatial Formats: Hands-on with Vector Data Workshop": "Workshops (Tuesday morning)",
    "FOSS4G with .NET: A Hands-On Introduction for Spatial Developers Workshop": "Workshops (Tuesday morning)",
    "GeoServer 3 Developers Workshop": "Workshops (Tuesday morning)",
    "Introduction to QField plugin authoring Workshop": "Workshops (Tuesday morning)",
    "Modelling Climate Risks Using NASA Earthdata Cloud & Python APIs Workshop": "Workshops (Tuesday morning)",
    "Oxidize to Decarbonize. Building more sustainable geospatial processes with Rust Workshop": "Workshops (Tuesday morning)",
    "pgRouting basic Workshop": "Workshops (Tuesday morning)",
    "Standalone Web Maps, No Platform Required Workshop": "Workshops (Tuesday morning)",
    "Terra Draw - cross-platform drawing library for all map applications Workshop": "Workshops (Tuesday morning)",
    # Tuesday afternoon
    "Building Spatial APIs in PostgreSQL with PostgREST Workshop": "Workshops (Tuesday afternoon)",
    "Collaborative Geospatial Workflows in Action: A Hands-On Alpha with Re:Earth Flow Workshop": "Workshops (Tuesday afternoon)",
    "Create and Customize Your Own 3D Web Maps with TerriaJS Workshop": "Workshops (Tuesday afternoon)",
    "Getting Started with GeoNetwork 5: A Hands-On Developer Workshop": "Workshops (Tuesday afternoon)",
    "H-O-T-T-O-G-O: Mobile Apps That Support Disaster Response and Climate Resilience Workshop": "Workshops (Tuesday afternoon)",
    "Open Data, Open Source, Open Standard: Quickly build your digital twin city with mago3D Workshop": "Workshops (Tuesday afternoon)",
    "Participatory mapping field survey and computer lab: QField integration into machine learning landcover classification within Digital Earth Pacific Workshop": "Workshops (Tuesday afternoon)",
    "Running and Auto Scaling Geoserver and PostgreSQL/PostGIS without managing servers in the AWS cloud Workshop": "Workshops (Tuesday afternoon)",
    "Semantic Interoperability made easy with OGC Building Blocks Workshop": "Workshops (Tuesday afternoon)",
    "Simulating Sustainable Urban Spaces on AWS Workshop": "Workshops (Tuesday afternoon)",
    "The Deep Magic of QGIS Cartography Workshop": "Workshops (Tuesday afternoon)",
}

KNOWN_ACTIVITIES = set(NON_WORKSHOP_ACTIVITIES + tuple(GROUPED.keys()))


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
        "Other": 0,
    }
    unknown_activity_names = set()
    for activity in activities["activities"]:
        if activity["name"] in KNOWN_ACTIVITIES:
            if activity["name"] in GROUPED:
                grouped_name = GROUPED[activity["name"]]
            else:
                grouped_name = activity["name"]
            if grouped_name in summary:
                if grouped_name not in NON_WORKSHOP_ACTIVITIES:
                    summary[grouped_name] += activity["allocation_count"]
                    print(f"Adding {activity['allocation_count']} to {grouped_name}")
                else:
                    # We don't want to sum things, just record the value once
                    # But log the old value
                    print(
                        f"Warning: {grouped_name} already in summary with value {summary[grouped_name]}, overwriting with {activity['allocation_count']}"
                    )
                    summary[grouped_name] = activity["allocation_count"]
            else:
                summary[grouped_name] = activity["allocation_count"]

        else:
            summary["Other"] += activity["allocation_count"]
            unknown_activity_names.add(activity["name"])

    print("Unknown activities found:", ", ".join(sorted(unknown_activity_names)))

    # Sort the summary by key
    summary = dict(sorted(summary.items()))

    return summary


def post_to_slack(
    webhook: str,
    summary: dict,
    event_date: datetime,
    timezone: str,
    dry_run: bool = False,
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
        [f"\t• {ticket_type}: {quantity}" for ticket_type, quantity in summary.items()]
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
