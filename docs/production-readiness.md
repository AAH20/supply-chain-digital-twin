# Production readiness boundary

Before using SupplyTwin for a real operational decision:

- Reconcile material, supplier, BOM, inventory, order and financial master data.
- Contract-test authorized ERP, WMS, TMS, MES, IoT and supplier connectors.
- Establish event idempotency, schema evolution, replay and dead-letter handling.
- Backtest forecasts across enough history, products and demand regimes.
- Monitor forecast bias, drift and service-level outcomes.
- Validate optimization constraints with planning, quality, finance and operations owners.
- Require approval for purchasing, substitution, production and customer-priority changes.
- Store decisions and source evidence in durable, immutable storage.
- Exercise regional recovery and degraded offline operation.
- Verify savings, cash release and protected contribution against financial ledgers.

Simulation is decision support; it is not safety, quality or financial authorization.
