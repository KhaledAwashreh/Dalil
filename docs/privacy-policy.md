# Privacy Policy — Dalil

**Last updated:** May 6, 2026

## Overview

Dalil is an internal consulting memory tool developed for use within Restaurant365. This privacy policy describes how the application handles data when connecting to Atlassian services.

## Data Collection

Dalil accesses the following data through the Atlassian API:

- **User profile information:** name, email address, and account ID (used for authentication)
- **Confluence content:** page titles and body content (used for knowledge ingestion)

## Data Usage

All data accessed through Atlassian is used solely for:

- Authenticating users to the application
- Ingesting Confluence content into the Dalil knowledge base for consulting workflows

## Data Storage

- OAuth tokens are stored locally in encrypted form using Fernet symmetric encryption.
- Ingested content is stored in a local MuninnDB instance.
- No data is transmitted to third-party services beyond the configured LLM provider.

## Data Sharing

Dalil does not sell, share, or distribute any user or Atlassian data to third parties.

## Data Retention

Users can remove their stored tokens at any time by running `dalil auth logout`. Ingested content can be cleared from any vault using `dalil vault clear`.

## Contact

For questions about this policy, contact: kawashreh@restaurant365.com
