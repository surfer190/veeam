# Veeam Client

Veeam Rest API Client or wrapper to make it easier to interact with the Veeam API.

[The Veeam API documentation](https://helpcenter.veeam.com/backup/rest/overview.html)

## Installation

    pip install veeam

## Usage

    from veeam.client import VeeamClient
    
    client = VeeamClient()

## Uploading to Pypi

Create the `dist` and `build` folders

    python setup.py sdist bdist_wheel

Upload to test pypi

    twine upload --repository testpypi dist/*

## Running Tests

    pytest

## Contributing

...