### Simple Transport

Transport management app for tanker and hazchem fleet operations on Frappe / ERPNext.

### What This App Adds

- Custom doctypes:
  - `Route Master`
  - `Trip`
  - `Fuel Request`
  - `Trip Expense` child table
- Dedicated role-based workspaces for transport executives, operations managers, and drivers
- Targeted ERPNext custom fields on:
  - `Sales Order` so it can act as the transport order / billing base
  - `Vehicle` for capacity, operational status, Fastag balance, and current trip
  - `Employee` for driver-specific licensing and hazchem details
  - `Trip` so it can act as the vehicle-wise Lorry Receipt

### Intended Flow

1. Create or maintain `Customer`, `Vehicle`, `Employee`, `Item`, and inventory masters in ERPNext.
2. Create `Route Master` for approved source-destination lanes and route-level rate / fuel standards.
3. Use `Sales Order` as the transport order with one freight service line, route, chemical, and shipment party details.
4. Create a `Trip` for each allocated vehicle-driver dispatch against the sales order and print the `Lorry Receipt` from the Trip.
5. Raise `Fuel Request` against the trip, then approve and disburse on the same document.
6. Track toll / octroi / Fastag / misc trip costs in the `Trip Expense` table.
7. Complete billing through standard `Sales Invoice`.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app simple_transport
```

If you are applying this to an existing site, run:

```bash
bench --site <your-site> install-app simple_transport
bench --site <your-site> migrate
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/simple_transport
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
