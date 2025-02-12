# Moya Python Private Set Intersection Library

Tooling to allow for secure querying of phone numbers against Moya's server using a technique called "Private Set
Intersection". This means that the numbers which are being queried never leave the client system. The trade-off is that
this is very slow and resource intensive. Use of the [standard user lookup](https://docs.moya.app/#user-lookups) API is
much preferred.

This is a heavily reworked version of https://github.com/bit-ml/Private-Set-Intersection/. The underlying encryption
and mathematics do not change, however the structure of the library is rebuilt with typing, tests and classes enabling
reuse elsewhere.

# Installation

    pip install .

# Usage

Create a file called numbers.txt with each phone number to query in normalized international format:

    27821234567
    27912345678
    44725881234
    ...

Then run the client:

    python client.py --token="YOUR_TOKEN" numbers.txt

This will output a count and the list of numbers which overlap.

# Development

## Installation for local development

    uv venv
    source .venv/bin/activate
    uv pip install -e .[dev]

## Linting

    poe fix
    poe lint

## Testing

    poe test
