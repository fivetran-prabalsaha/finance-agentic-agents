"""
Deploy the AR Collection Agent to Vertex AI Agent Engine.

Usage:
    python deploy.py                  # create new deployment
    python deploy.py --update RESOURCE_NAME   # update existing deployment
    python deploy.py --delete RESOURCE_NAME   # tear down

Prerequisites:
    gcloud auth application-default login
    gcloud config set project $GOOGLE_CLOUD_PROJECT
"""
import argparse
import os

import vertexai
from dotenv import load_dotenv
from vertexai import agent_engines

from agent import root_agent

load_dotenv()

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
DISPLAY_NAME = "ar-collection-agent"

REQUIREMENTS = [
    "google-adk>=0.4.0",
    "google-cloud-aiplatform[agent_engines,adk]>=1.75.0",
    "python-dotenv>=1.0.0",
]

EXTRA_PACKAGES = [
    "./tools.py",
]


def create() -> None:
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    app = agent_engines.AdkApp(agent=root_agent, enable_tracing=True)

    remote = agent_engines.create(
        app,
        requirements=REQUIREMENTS,
        extra_packages=EXTRA_PACKAGES,
        display_name=DISPLAY_NAME,
        description="AR Collection multi-agent: router → synthesizer (NetSuite) / escalator (Jira)",
    )
    print(f"Created: {remote.resource_name}")


def update(resource_name: str) -> None:
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    app = agent_engines.AdkApp(agent=root_agent, enable_tracing=True)
    remote = agent_engines.get(resource_name)
    remote.update(agent_engine=app, requirements=REQUIREMENTS)
    print(f"Updated: {resource_name}")


def delete(resource_name: str) -> None:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    agent_engines.delete(resource_name, force=True)
    print(f"Deleted: {resource_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--update", metavar="RESOURCE_NAME")
    group.add_argument("--delete", metavar="RESOURCE_NAME")
    args = parser.parse_args()

    if args.update:
        update(args.update)
    elif args.delete:
        delete(args.delete)
    else:
        create()
