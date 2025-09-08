# Tito to Slack Reporting Script

An integration between Tito and Slack to post an update on how many tickets have been sold.

## Requirements

Fork the repo and set the github repo up with the following variables:

* ACCOUNT: your tito account
* EVENT: your tito event.

And the following secrets:

* TITO_KEY: your Tito API Key
* SLACK_WEBHOOK: a webhook for a channel on Slack


## Test locally

Run the command:

```bash
python tito_slack/tito_slack.py --summary-type=activities osgeo-oceania foss4g-2025 2025-11-11
```

And if you add `--dry-run` then it won't post to Slack.
