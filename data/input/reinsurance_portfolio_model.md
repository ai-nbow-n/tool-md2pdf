# Complex Reinsurance Portfolio Data Model and Curated Mock Data

This document defines a realistic ceded reinsurance portfolio model for PostgreSQL with Rust `sqlx` type mappings. It includes contract wording and versioning, treaty accounts and statements, cash settlements, technical accounting, IBNR, commutations, sanctions and KYC, loss corridors, sliding-scale commissions, aggregate erosion, event aggregation, reinstatement erosion, reserve histories, retrocession, and multi-currency valuation. All UUIDs in the mock data are complete and every foreign key shown in the mock dataset resolves to another row in this document.

## Type conventions

- `UUID` → `uuid::Uuid`
- `NUMERIC(p,s)` → `rust_decimal::Decimal`
- nullable SQL columns → `Option<T>` in Rust
- `DATE` → `chrono::NaiveDate`
- `TIMESTAMPTZ` → `chrono::DateTime<Utc>`
- `JSONB` → `serde_json::Value`

## Data model

### `legal_entity`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| legal_entity_id | Yes | — | UUID / uuid::Uuid | No |
| entity_code | No | — | VARCHAR(30) / String | No |
| entity_name | No | — | VARCHAR(200) / String | No |
| lei | No | — | VARCHAR(20) / String | Yes |
| country_code | No | — | CHAR(2) / String | No |
| base_currency | No | — | CHAR(3) / String | No |
| entity_type | No | — | VARCHAR(30) / String | No |
| active | No | — | BOOLEAN / bool | No |

### `counterparty`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| counterparty_id | Yes | — | UUID / uuid::Uuid | No |
| counterparty_code | No | — | VARCHAR(30) / String | No |
| counterparty_name | No | — | VARCHAR(200) / String | No |
| counterparty_type | No | — | VARCHAR(30) / String | No |
| lei | No | — | VARCHAR(20) / String | Yes |
| country_code | No | — | CHAR(2) / String | No |
| rating_agency | No | — | VARCHAR(30) / String | Yes |
| financial_rating | No | — | VARCHAR(10) / String | Yes |
| collateral_required | No | — | BOOLEAN / bool | No |
| active | No | — | BOOLEAN / bool | No |

### `broker`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| broker_id | Yes | — | UUID / uuid::Uuid | No |
| broker_code | No | — | VARCHAR(30) / String | No |
| broker_name | No | — | VARCHAR(200) / String | No |
| country_code | No | — | CHAR(2) / String | No |
| license_reference | No | — | VARCHAR(100) / String | Yes |
| contact_email | No | — | VARCHAR(200) / String | Yes |
| active | No | — | BOOLEAN / bool | No |

### `portfolio_type`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| portfolio_type_id | Yes | — | UUID / uuid::Uuid | No |
| portfolio_type_code | No | — | VARCHAR(40) / String | No |
| portfolio_type_name | No | — | VARCHAR(120) / String | No |
| reinsurance_family | No | — | VARCHAR(40) / String | No |
| default_attachment_basis | No | — | VARCHAR(30) / String | No |
| default_accounting_basis | No | — | VARCHAR(30) / String | No |
| description | No | — | TEXT / String | No |

### `reinsurance_program`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| program_id | Yes | — | UUID / uuid::Uuid | No |
| ceding_entity_id | No | legal_entity.legal_entity_id | UUID / uuid::Uuid | No |
| portfolio_type_id | No | portfolio_type.portfolio_type_id | UUID / uuid::Uuid | No |
| program_code | No | — | VARCHAR(40) / String | No |
| program_name | No | — | VARCHAR(200) / String | No |
| underwriting_year | No | — | SMALLINT / i16 | No |
| business_unit | No | — | VARCHAR(100) / String | No |
| target_currency | No | — | CHAR(3) / String | No |
| status | No | — | VARCHAR(20) / String | No |

### `reinsurance_contract`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| contract_id | Yes | — | UUID / uuid::Uuid | No |
| program_id | No | reinsurance_program.program_id | UUID / uuid::Uuid | No |
| broker_id | No | broker.broker_id | UUID / uuid::Uuid | Yes |
| contract_number | No | — | VARCHAR(50) / String | No |
| contract_name | No | — | VARCHAR(200) / String | No |
| contract_type | No | — | VARCHAR(40) / String | No |
| underwriting_year | No | — | SMALLINT / i16 | No |
| effective_date | No | — | DATE / chrono::NaiveDate | No |
| expiry_date | No | — | DATE / chrono::NaiveDate | No |
| currency_code | No | — | CHAR(3) / String | No |
| attachment_basis | No | — | VARCHAR(30) / String | No |
| accounting_basis | No | — | VARCHAR(30) / String | No |
| governing_law | No | — | VARCHAR(100) / String | Yes |
| status | No | — | VARCHAR(20) / String | No |
| terms_json | No | — | JSONB / serde_json::Value | Yes |

### `contract_version`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| contract_version_id | Yes | — | UUID / uuid::Uuid | No |
| contract_id | No | reinsurance_contract.contract_id | UUID / uuid::Uuid | No |
| version_no | No | — | INTEGER / i32 | No |
| version_status | No | — | VARCHAR(20) / String | No |
| effective_from | No | — | DATE / chrono::NaiveDate | No |
| effective_to | No | — | DATE / chrono::NaiveDate | Yes |
| signed_date | No | — | DATE / chrono::NaiveDate | Yes |
| wording_reference | No | — | VARCHAR(100) / String | No |
| wording_hash_sha256 | No | — | CHAR(64) / String | No |
| change_reason | No | — | TEXT / String | Yes |

### `contract_wording_clause`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| wording_clause_id | Yes | — | UUID / uuid::Uuid | No |
| contract_version_id | No | contract_version.contract_version_id | UUID / uuid::Uuid | No |
| clause_code | No | — | VARCHAR(40) / String | No |
| clause_title | No | — | VARCHAR(200) / String | No |
| clause_category | No | — | VARCHAR(50) / String | No |
| clause_sequence | No | — | INTEGER / i32 | No |
| clause_text | No | — | TEXT / String | No |
| is_manuscript | No | — | BOOLEAN / bool | No |

### `contract_section`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| section_id | Yes | — | UUID / uuid::Uuid | No |
| contract_id | No | reinsurance_contract.contract_id | UUID / uuid::Uuid | No |
| section_code | No | — | VARCHAR(30) / String | No |
| section_name | No | — | VARCHAR(200) / String | No |
| line_of_business | No | — | VARCHAR(50) / String | No |
| territory_scope | No | — | VARCHAR(100) / String | No |
| coverage_basis | No | — | VARCHAR(30) / String | No |
| inuring_priority | No | — | SMALLINT / i16 | No |
| hours_clause | No | — | SMALLINT / i16 | Yes |
| annual_aggregate_deductible | No | — | NUMERIC(20,2) / rust_decimal::Decimal | Yes |
| annual_aggregate_limit | No | — | NUMERIC(20,2) / rust_decimal::Decimal | Yes |
| currency_code | No | — | CHAR(3) / String | No |

### `reinsurance_layer`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| layer_id | Yes | — | UUID / uuid::Uuid | No |
| section_id | No | contract_section.section_id | UUID / uuid::Uuid | No |
| layer_no | No | — | SMALLINT / i16 | No |
| layer_name | No | — | VARCHAR(100) / String | No |
| layer_type | No | — | VARCHAR(40) / String | No |
| attachment_point | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| layer_limit | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| annual_aggregate_limit | No | — | NUMERIC(20,2) / rust_decimal::Decimal | Yes |
| rate_on_line_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | Yes |
| minimum_deposit_premium | No | — | NUMERIC(20,2) / rust_decimal::Decimal | Yes |
| adjustable_premium_rate_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | Yes |
| reinstatement_count | No | — | SMALLINT / i16 | Yes |
| reinstatement_rate_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | Yes |
| currency_code | No | — | CHAR(3) / String | No |

### `loss_corridor`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| loss_corridor_id | Yes | — | UUID / uuid::Uuid | No |
| section_id | No | contract_section.section_id | UUID / uuid::Uuid | No |
| corridor_basis | No | — | VARCHAR(30) / String | No |
| lower_loss_ratio_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| upper_loss_ratio_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| cedent_share_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| reinsurer_share_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| annual_cap | No | — | NUMERIC(20,2) / rust_decimal::Decimal | Yes |
| currency_code | No | — | CHAR(3) / String | No |

### `sliding_scale_commission`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| sliding_scale_id | Yes | — | UUID / uuid::Uuid | No |
| section_id | No | contract_section.section_id | UUID / uuid::Uuid | No |
| loss_ratio_from_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| loss_ratio_to_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| commission_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| provisional_commission_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| calculation_sequence | No | — | SMALLINT / i16 | No |

### `layer_participation`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| participation_id | Yes | — | UUID / uuid::Uuid | No |
| layer_id | No | reinsurance_layer.layer_id | UUID / uuid::Uuid | No |
| reinsurer_id | No | counterparty.counterparty_id | UUID / uuid::Uuid | No |
| written_share_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| signed_share_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| brokerage_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| reinsurance_tax_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| commission_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | Yes |
| effective_from | No | — | DATE / chrono::NaiveDate | No |
| effective_to | No | — | DATE / chrono::NaiveDate | Yes |
| status | No | — | VARCHAR(20) / String | No |

### `insured`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| insured_id | Yes | — | UUID / uuid::Uuid | No |
| insured_number | No | — | VARCHAR(50) / String | No |
| insured_name | No | — | VARCHAR(200) / String | No |
| industry_code | No | — | VARCHAR(20) / String | Yes |
| industry_description | No | — | VARCHAR(100) / String | Yes |
| country_code | No | — | CHAR(2) / String | No |
| group_name | No | — | VARCHAR(200) / String | Yes |
| active | No | — | BOOLEAN / bool | No |

### `underlying_policy`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| policy_id | Yes | — | UUID / uuid::Uuid | No |
| ceding_entity_id | No | legal_entity.legal_entity_id | UUID / uuid::Uuid | No |
| insured_id | No | insured.insured_id | UUID / uuid::Uuid | No |
| policy_number | No | — | VARCHAR(50) / String | No |
| line_of_business | No | — | VARCHAR(50) / String | No |
| inception_date | No | — | DATE / chrono::NaiveDate | No |
| expiry_date | No | — | DATE / chrono::NaiveDate | No |
| currency_code | No | — | CHAR(3) / String | No |
| gross_written_premium | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| sum_insured | No | — | NUMERIC(20,2) / rust_decimal::Decimal | Yes |
| policy_limit | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| deductible | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| status | No | — | VARCHAR(20) / String | No |
| metadata_json | No | — | JSONB / serde_json::Value | Yes |

### `risk_location`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| location_id | Yes | — | UUID / uuid::Uuid | No |
| policy_id | No | underlying_policy.policy_id | UUID / uuid::Uuid | No |
| location_number | No | — | VARCHAR(30) / String | No |
| address_line1 | No | — | VARCHAR(200) / String | No |
| city | No | — | VARCHAR(100) / String | No |
| postal_code | No | — | VARCHAR(20) / String | No |
| country_code | No | — | CHAR(2) / String | No |
| latitude | No | — | NUMERIC(9,6) / rust_decimal::Decimal | Yes |
| longitude | No | — | NUMERIC(9,6) / rust_decimal::Decimal | Yes |
| occupancy_code | No | — | VARCHAR(30) / String | Yes |
| construction_code | No | — | VARCHAR(30) / String | Yes |

### `exposure`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| exposure_id | Yes | — | UUID / uuid::Uuid | No |
| policy_id | No | underlying_policy.policy_id | UUID / uuid::Uuid | No |
| location_id | No | risk_location.location_id | UUID / uuid::Uuid | Yes |
| exposure_type | No | — | VARCHAR(30) / String | No |
| currency_code | No | — | CHAR(3) / String | No |
| tiv | No | — | NUMERIC(20,2) / rust_decimal::Decimal | Yes |
| policy_limit_allocated | No | — | NUMERIC(20,2) / rust_decimal::Decimal | Yes |
| deductible_allocated | No | — | NUMERIC(20,2) / rust_decimal::Decimal | Yes |
| business_interruption_days | No | — | INTEGER / i32 | Yes |
| peril_codes_json | No | — | JSONB / serde_json::Value | Yes |
| as_of_date | No | — | DATE / chrono::NaiveDate | No |

### `policy_section_allocation`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| allocation_id | Yes | — | UUID / uuid::Uuid | No |
| policy_id | No | underlying_policy.policy_id | UUID / uuid::Uuid | No |
| section_id | No | contract_section.section_id | UUID / uuid::Uuid | No |
| ceded_share_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| subject_premium | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| subject_sum_insured | No | — | NUMERIC(20,2) / rust_decimal::Decimal | Yes |
| effective_from | No | — | DATE / chrono::NaiveDate | No |
| effective_to | No | — | DATE / chrono::NaiveDate | Yes |

### `bordereau_batch`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| bordereau_batch_id | Yes | — | UUID / uuid::Uuid | No |
| contract_id | No | reinsurance_contract.contract_id | UUID / uuid::Uuid | No |
| batch_type | No | — | VARCHAR(20) / String | No |
| reporting_period_start | No | — | DATE / chrono::NaiveDate | No |
| reporting_period_end | No | — | DATE / chrono::NaiveDate | No |
| received_at | No | — | TIMESTAMPTZ / chrono::DateTime<Utc> | No |
| source_filename | No | — | VARCHAR(255) / String | Yes |
| source_system | No | — | VARCHAR(50) / String | No |
| record_count | No | — | INTEGER / i32 | No |
| status | No | — | VARCHAR(20) / String | No |

### `premium_transaction`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| premium_tx_id | Yes | — | UUID / uuid::Uuid | No |
| bordereau_batch_id | No | bordereau_batch.bordereau_batch_id | UUID / uuid::Uuid | Yes |
| policy_id | No | underlying_policy.policy_id | UUID / uuid::Uuid | Yes |
| section_id | No | contract_section.section_id | UUID / uuid::Uuid | No |
| layer_id | No | reinsurance_layer.layer_id | UUID / uuid::Uuid | Yes |
| transaction_type | No | — | VARCHAR(30) / String | No |
| transaction_date | No | — | DATE / chrono::NaiveDate | No |
| accounting_period | No | — | DATE / chrono::NaiveDate | No |
| original_currency | No | — | CHAR(3) / String | No |
| gross_premium | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| subject_premium | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| ceded_premium | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| brokerage_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| tax_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| settlement_currency | No | — | CHAR(3) / String | No |
| fx_rate_to_contract | No | — | NUMERIC(18,8) / rust_decimal::Decimal | No |

### `catastrophe_event`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| event_id | Yes | — | UUID / uuid::Uuid | No |
| event_code | No | — | VARCHAR(40) / String | No |
| event_name | No | — | VARCHAR(200) / String | No |
| peril | No | — | VARCHAR(50) / String | No |
| start_date | No | — | DATE / chrono::NaiveDate | No |
| end_date | No | — | DATE / chrono::NaiveDate | Yes |
| region | No | — | VARCHAR(100) / String | No |
| external_event_code | No | — | VARCHAR(50) / String | Yes |

### `event_aggregation`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| event_aggregation_id | Yes | — | UUID / uuid::Uuid | No |
| event_id | No | catastrophe_event.event_id | UUID / uuid::Uuid | No |
| section_id | No | contract_section.section_id | UUID / uuid::Uuid | No |
| aggregation_key | No | — | VARCHAR(100) / String | No |
| hours_window_start | No | — | TIMESTAMPTZ / chrono::DateTime<Utc> | No |
| hours_window_end | No | — | TIMESTAMPTZ / chrono::DateTime<Utc> | No |
| gross_loss | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| ceded_loss_before_limits | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |
| status | No | — | VARCHAR(20) / String | No |

### `claim`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| claim_id | Yes | — | UUID / uuid::Uuid | No |
| policy_id | No | underlying_policy.policy_id | UUID / uuid::Uuid | No |
| location_id | No | risk_location.location_id | UUID / uuid::Uuid | Yes |
| event_id | No | catastrophe_event.event_id | UUID / uuid::Uuid | Yes |
| claim_number | No | — | VARCHAR(50) / String | No |
| loss_date | No | — | DATE / chrono::NaiveDate | No |
| reported_date | No | — | DATE / chrono::NaiveDate | No |
| cause_of_loss | No | — | VARCHAR(100) / String | No |
| original_currency | No | — | CHAR(3) / String | No |
| gross_incurred | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| gross_paid | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| case_reserve | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| status | No | — | VARCHAR(20) / String | No |

### `claim_transaction`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| claim_tx_id | Yes | — | UUID / uuid::Uuid | No |
| claim_id | No | claim.claim_id | UUID / uuid::Uuid | No |
| transaction_date | No | — | DATE / chrono::NaiveDate | No |
| accounting_period | No | — | DATE / chrono::NaiveDate | No |
| movement_type | No | — | VARCHAR(30) / String | No |
| currency_code | No | — | CHAR(3) / String | No |
| loss_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| expense_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| salvage_subrogation_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| fx_rate_to_policy | No | — | NUMERIC(18,8) / rust_decimal::Decimal | No |

### `claim_reserve_history`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| reserve_history_id | Yes | — | UUID / uuid::Uuid | No |
| claim_id | No | claim.claim_id | UUID / uuid::Uuid | No |
| valuation_date | No | — | DATE / chrono::NaiveDate | No |
| case_indemnity_reserve | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| case_expense_reserve | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| ceded_case_reserve | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |
| reserve_method | No | — | VARCHAR(40) / String | No |

### `ibnr_estimate`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| ibnr_estimate_id | Yes | — | UUID / uuid::Uuid | No |
| program_id | No | reinsurance_program.program_id | UUID / uuid::Uuid | No |
| section_id | No | contract_section.section_id | UUID / uuid::Uuid | Yes |
| valuation_date | No | — | DATE / chrono::NaiveDate | No |
| accident_year | No | — | SMALLINT / i16 | No |
| method | No | — | VARCHAR(40) / String | No |
| gross_ibnr | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| ceded_ibnr | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |
| model_version | No | — | VARCHAR(30) / String | No |

### `recovery_allocation`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| recovery_allocation_id | Yes | — | UUID / uuid::Uuid | No |
| claim_tx_id | No | claim_transaction.claim_tx_id | UUID / uuid::Uuid | No |
| layer_id | No | reinsurance_layer.layer_id | UUID / uuid::Uuid | No |
| participation_id | No | layer_participation.participation_id | UUID / uuid::Uuid | No |
| calculation_basis | No | — | VARCHAR(30) / String | No |
| gross_layer_recovery | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| reinsurer_share_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| reinsurer_recovery | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |
| status | No | — | VARCHAR(20) / String | No |
| recognized_date | No | — | DATE / chrono::NaiveDate | No |
| settled_date | No | — | DATE / chrono::NaiveDate | Yes |

### `aggregate_erosion`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| aggregate_erosion_id | Yes | — | UUID / uuid::Uuid | No |
| layer_id | No | reinsurance_layer.layer_id | UUID / uuid::Uuid | No |
| claim_tx_id | No | claim_transaction.claim_tx_id | UUID / uuid::Uuid | Yes |
| event_aggregation_id | No | event_aggregation.event_aggregation_id | UUID / uuid::Uuid | Yes |
| valuation_date | No | — | DATE / chrono::NaiveDate | No |
| erosion_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| cumulative_erosion | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| remaining_aggregate_limit | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |

### `reinstatement`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| reinstatement_id | Yes | — | UUID / uuid::Uuid | No |
| layer_id | No | reinsurance_layer.layer_id | UUID / uuid::Uuid | No |
| trigger_claim_id | No | claim.claim_id | UUID / uuid::Uuid | No |
| reinstatement_no | No | — | SMALLINT / i16 | No |
| triggered_date | No | — | DATE / chrono::NaiveDate | No |
| reinstated_limit | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| premium_rate_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| reinstatement_premium | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |
| status | No | — | VARCHAR(20) / String | No |

### `reinstatement_erosion`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| reinstatement_erosion_id | Yes | — | UUID / uuid::Uuid | No |
| reinstatement_id | No | reinstatement.reinstatement_id | UUID / uuid::Uuid | No |
| claim_tx_id | No | claim_transaction.claim_tx_id | UUID / uuid::Uuid | No |
| erosion_date | No | — | DATE / chrono::NaiveDate | No |
| erosion_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| cumulative_erosion | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| remaining_reinstated_limit | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |

### `treaty_account`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| treaty_account_id | Yes | — | UUID / uuid::Uuid | No |
| contract_id | No | reinsurance_contract.contract_id | UUID / uuid::Uuid | No |
| account_period_start | No | — | DATE / chrono::NaiveDate | No |
| account_period_end | No | — | DATE / chrono::NaiveDate | No |
| account_type | No | — | VARCHAR(30) / String | No |
| currency_code | No | — | CHAR(3) / String | No |
| premium_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| claims_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| commission_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| brokerage_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| tax_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| balance_due | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| status | No | — | VARCHAR(20) / String | No |

### `treaty_statement`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| treaty_statement_id | Yes | — | UUID / uuid::Uuid | No |
| treaty_account_id | No | treaty_account.treaty_account_id | UUID / uuid::Uuid | No |
| participation_id | No | layer_participation.participation_id | UUID / uuid::Uuid | Yes |
| statement_number | No | — | VARCHAR(60) / String | No |
| statement_date | No | — | DATE / chrono::NaiveDate | No |
| due_date | No | — | DATE / chrono::NaiveDate | No |
| statement_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |
| status | No | — | VARCHAR(20) / String | No |

### `technical_accounting_entry`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| technical_entry_id | Yes | — | UUID / uuid::Uuid | No |
| contract_id | No | reinsurance_contract.contract_id | UUID / uuid::Uuid | No |
| section_id | No | contract_section.section_id | UUID / uuid::Uuid | Yes |
| participation_id | No | layer_participation.participation_id | UUID / uuid::Uuid | Yes |
| source_type | No | — | VARCHAR(30) / String | No |
| source_reference | No | — | VARCHAR(80) / String | No |
| posting_date | No | — | DATE / chrono::NaiveDate | No |
| accounting_period | No | — | DATE / chrono::NaiveDate | No |
| ledger_account | No | — | VARCHAR(40) / String | No |
| debit_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| credit_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |
| status | No | — | VARCHAR(20) / String | No |

### `cash_settlement`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| cash_settlement_id | Yes | — | UUID / uuid::Uuid | No |
| treaty_statement_id | No | treaty_statement.treaty_statement_id | UUID / uuid::Uuid | Yes |
| counterparty_id | No | counterparty.counterparty_id | UUID / uuid::Uuid | No |
| settlement_reference | No | — | VARCHAR(80) / String | No |
| value_date | No | — | DATE / chrono::NaiveDate | No |
| direction | No | — | VARCHAR(10) / String | No |
| amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |
| bank_reference | No | — | VARCHAR(100) / String | Yes |
| status | No | — | VARCHAR(20) / String | No |

### `collateral`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| collateral_id | Yes | — | UUID / uuid::Uuid | No |
| participation_id | No | layer_participation.participation_id | UUID / uuid::Uuid | No |
| collateral_type | No | — | VARCHAR(30) / String | No |
| provider_name | No | — | VARCHAR(200) / String | Yes |
| instrument_reference | No | — | VARCHAR(100) / String | Yes |
| valuation_date | No | — | DATE / chrono::NaiveDate | No |
| amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |
| expiry_date | No | — | DATE / chrono::NaiveDate | Yes |
| status | No | — | VARCHAR(20) / String | No |

### `kyc_review`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| kyc_review_id | Yes | — | UUID / uuid::Uuid | No |
| counterparty_id | No | counterparty.counterparty_id | UUID / uuid::Uuid | No |
| review_date | No | — | DATE / chrono::NaiveDate | No |
| review_type | No | — | VARCHAR(30) / String | No |
| risk_rating | No | — | VARCHAR(20) / String | No |
| beneficial_owner_verified | No | — | BOOLEAN / bool | No |
| source_of_funds_verified | No | — | BOOLEAN / bool | No |
| next_review_date | No | — | DATE / chrono::NaiveDate | No |
| status | No | — | VARCHAR(20) / String | No |

### `sanctions_screening`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| sanctions_screening_id | Yes | — | UUID / uuid::Uuid | No |
| counterparty_id | No | counterparty.counterparty_id | UUID / uuid::Uuid | No |
| screened_at | No | — | TIMESTAMPTZ / chrono::DateTime<Utc> | No |
| provider | No | — | VARCHAR(50) / String | No |
| screening_list_set | No | — | VARCHAR(100) / String | No |
| match_status | No | — | VARCHAR(20) / String | No |
| match_score | No | — | NUMERIC(5,2) / rust_decimal::Decimal | Yes |
| case_reference | No | — | VARCHAR(80) / String | Yes |
| disposition | No | — | VARCHAR(40) / String | No |

### `commutation`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| commutation_id | Yes | — | UUID / uuid::Uuid | No |
| ceding_entity_id | No | legal_entity.legal_entity_id | UUID / uuid::Uuid | No |
| counterparty_id | No | counterparty.counterparty_id | UUID / uuid::Uuid | No |
| commutation_reference | No | — | VARCHAR(80) / String | No |
| agreement_date | No | — | DATE / chrono::NaiveDate | No |
| effective_date | No | — | DATE / chrono::NaiveDate | No |
| settlement_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |
| release_scope | No | — | TEXT / String | No |
| status | No | — | VARCHAR(20) / String | No |

### `commutation_contract`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| commutation_contract_id | Yes | — | UUID / uuid::Uuid | No |
| commutation_id | No | commutation.commutation_id | UUID / uuid::Uuid | No |
| contract_id | No | reinsurance_contract.contract_id | UUID / uuid::Uuid | No |
| allocated_settlement_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |

### `retrocession_program`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| retro_program_id | Yes | — | UUID / uuid::Uuid | No |
| owner_counterparty_id | No | counterparty.counterparty_id | UUID / uuid::Uuid | No |
| retro_program_code | No | — | VARCHAR(40) / String | No |
| program_name | No | — | VARCHAR(200) / String | No |
| underwriting_year | No | — | SMALLINT / i16 | No |
| currency_code | No | — | CHAR(3) / String | No |
| status | No | — | VARCHAR(20) / String | No |

### `retrocession_contract`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| retro_contract_id | Yes | — | UUID / uuid::Uuid | No |
| retro_program_id | No | retrocession_program.retro_program_id | UUID / uuid::Uuid | No |
| source_contract_id | No | reinsurance_contract.contract_id | UUID / uuid::Uuid | No |
| contract_number | No | — | VARCHAR(50) / String | No |
| contract_type | No | — | VARCHAR(40) / String | No |
| effective_date | No | — | DATE / chrono::NaiveDate | No |
| expiry_date | No | — | DATE / chrono::NaiveDate | No |
| currency_code | No | — | CHAR(3) / String | No |
| status | No | — | VARCHAR(20) / String | No |

### `retrocession_layer`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| retro_layer_id | Yes | — | UUID / uuid::Uuid | No |
| retro_contract_id | No | retrocession_contract.retro_contract_id | UUID / uuid::Uuid | No |
| source_layer_id | No | reinsurance_layer.layer_id | UUID / uuid::Uuid | No |
| layer_no | No | — | SMALLINT / i16 | No |
| attachment_point | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| layer_limit | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| ceded_share_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| currency_code | No | — | CHAR(3) / String | No |

### `retrocession_participation`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| retro_participation_id | Yes | — | UUID / uuid::Uuid | No |
| retro_layer_id | No | retrocession_layer.retro_layer_id | UUID / uuid::Uuid | No |
| retrocessionaire_id | No | counterparty.counterparty_id | UUID / uuid::Uuid | No |
| signed_share_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| brokerage_pct | No | — | NUMERIC(9,6) / rust_decimal::Decimal | No |
| status | No | — | VARCHAR(20) / String | No |

### `multi_currency_valuation`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| valuation_id | Yes | — | UUID / uuid::Uuid | No |
| valuation_date | No | — | DATE / chrono::NaiveDate | No |
| object_type | No | — | VARCHAR(30) / String | No |
| object_id | No | — | UUID / uuid::Uuid | No |
| original_currency | No | — | CHAR(3) / String | No |
| original_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| functional_currency | No | — | CHAR(3) / String | No |
| functional_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| reporting_currency | No | — | CHAR(3) / String | No |
| reporting_amount | No | — | NUMERIC(20,2) / rust_decimal::Decimal | No |
| fx_rate_original_to_functional | No | — | NUMERIC(18,8) / rust_decimal::Decimal | No |
| fx_rate_functional_to_reporting | No | — | NUMERIC(18,8) / rust_decimal::Decimal | No |
| valuation_basis | No | — | VARCHAR(30) / String | No |

### `fx_rate`

| Field name | PK | FK | Data type (SQLx) | Nullable |
| --- | --- | --- | --- | --- |
| fx_rate_id | Yes | — | UUID / uuid::Uuid | No |
| rate_date | No | — | DATE / chrono::NaiveDate | No |
| base_currency | No | — | CHAR(3) / String | No |
| quote_currency | No | — | CHAR(3) / String | No |
| rate | No | — | NUMERIC(18,8) / rust_decimal::Decimal | No |
| rate_type | No | — | VARCHAR(20) / String | No |
| source | No | — | VARCHAR(50) / String | No |

## Exact ER diagram

The diagram contains every modeled field. Mermaid scalar types are simplified, while entity names, field names, PK markers, FK markers, and relationships match the tabular model.

```mermaid
erDiagram
    LEGAL_ENTITY {
        uuid legal_entity_id PK
        string entity_code
        string entity_name
        string lei
        string country_code
        string base_currency
        string entity_type
        boolean active
    }
    COUNTERPARTY {
        uuid counterparty_id PK
        string counterparty_code
        string counterparty_name
        string counterparty_type
        string lei
        string country_code
        string rating_agency
        string financial_rating
        boolean collateral_required
        boolean active
    }
    BROKER {
        uuid broker_id PK
        string broker_code
        string broker_name
        string country_code
        string license_reference
        string contact_email
        boolean active
    }
    PORTFOLIO_TYPE {
        uuid portfolio_type_id PK
        string portfolio_type_code
        string portfolio_type_name
        string reinsurance_family
        string default_attachment_basis
        string default_accounting_basis
        string description
    }
    REINSURANCE_PROGRAM {
        uuid program_id PK
        uuid ceding_entity_id FK
        uuid portfolio_type_id FK
        string program_code
        string program_name
        int underwriting_year
        string business_unit
        string target_currency
        string status
    }
    REINSURANCE_CONTRACT {
        uuid contract_id PK
        uuid program_id FK
        uuid broker_id FK
        string contract_number
        string contract_name
        string contract_type
        int underwriting_year
        date effective_date
        date expiry_date
        string currency_code
        string attachment_basis
        string accounting_basis
        string governing_law
        string status
        json terms_json
    }
    CONTRACT_VERSION {
        uuid contract_version_id PK
        uuid contract_id FK
        int version_no
        string version_status
        date effective_from
        date effective_to
        date signed_date
        string wording_reference
        string wording_hash_sha256
        string change_reason
    }
    CONTRACT_WORDING_CLAUSE {
        uuid wording_clause_id PK
        uuid contract_version_id FK
        string clause_code
        string clause_title
        string clause_category
        int clause_sequence
        string clause_text
        boolean is_manuscript
    }
    CONTRACT_SECTION {
        uuid section_id PK
        uuid contract_id FK
        string section_code
        string section_name
        string line_of_business
        string territory_scope
        string coverage_basis
        int inuring_priority
        int hours_clause
        decimal annual_aggregate_deductible
        decimal annual_aggregate_limit
        string currency_code
    }
    REINSURANCE_LAYER {
        uuid layer_id PK
        uuid section_id FK
        int layer_no
        string layer_name
        string layer_type
        decimal attachment_point
        decimal layer_limit
        decimal annual_aggregate_limit
        decimal rate_on_line_pct
        decimal minimum_deposit_premium
        decimal adjustable_premium_rate_pct
        int reinstatement_count
        decimal reinstatement_rate_pct
        string currency_code
    }
    LOSS_CORRIDOR {
        uuid loss_corridor_id PK
        uuid section_id FK
        string corridor_basis
        decimal lower_loss_ratio_pct
        decimal upper_loss_ratio_pct
        decimal cedent_share_pct
        decimal reinsurer_share_pct
        decimal annual_cap
        string currency_code
    }
    SLIDING_SCALE_COMMISSION {
        uuid sliding_scale_id PK
        uuid section_id FK
        decimal loss_ratio_from_pct
        decimal loss_ratio_to_pct
        decimal commission_pct
        decimal provisional_commission_pct
        int calculation_sequence
    }
    LAYER_PARTICIPATION {
        uuid participation_id PK
        uuid layer_id FK
        uuid reinsurer_id FK
        decimal written_share_pct
        decimal signed_share_pct
        decimal brokerage_pct
        decimal reinsurance_tax_pct
        decimal commission_pct
        date effective_from
        date effective_to
        string status
    }
    INSURED {
        uuid insured_id PK
        string insured_number
        string insured_name
        string industry_code
        string industry_description
        string country_code
        string group_name
        boolean active
    }
    UNDERLYING_POLICY {
        uuid policy_id PK
        uuid ceding_entity_id FK
        uuid insured_id FK
        string policy_number
        string line_of_business
        date inception_date
        date expiry_date
        string currency_code
        decimal gross_written_premium
        decimal sum_insured
        decimal policy_limit
        decimal deductible
        string status
        json metadata_json
    }
    RISK_LOCATION {
        uuid location_id PK
        uuid policy_id FK
        string location_number
        string address_line1
        string city
        string postal_code
        string country_code
        decimal latitude
        decimal longitude
        string occupancy_code
        string construction_code
    }
    EXPOSURE {
        uuid exposure_id PK
        uuid policy_id FK
        uuid location_id FK
        string exposure_type
        string currency_code
        decimal tiv
        decimal policy_limit_allocated
        decimal deductible_allocated
        int business_interruption_days
        json peril_codes_json
        date as_of_date
    }
    POLICY_SECTION_ALLOCATION {
        uuid allocation_id PK
        uuid policy_id FK
        uuid section_id FK
        decimal ceded_share_pct
        decimal subject_premium
        decimal subject_sum_insured
        date effective_from
        date effective_to
    }
    BORDEREAU_BATCH {
        uuid bordereau_batch_id PK
        uuid contract_id FK
        string batch_type
        date reporting_period_start
        date reporting_period_end
        datetime received_at
        string source_filename
        string source_system
        int record_count
        string status
    }
    PREMIUM_TRANSACTION {
        uuid premium_tx_id PK
        uuid bordereau_batch_id FK
        uuid policy_id FK
        uuid section_id FK
        uuid layer_id FK
        string transaction_type
        date transaction_date
        date accounting_period
        string original_currency
        decimal gross_premium
        decimal subject_premium
        decimal ceded_premium
        decimal brokerage_amount
        decimal tax_amount
        string settlement_currency
        decimal fx_rate_to_contract
    }
    CATASTROPHE_EVENT {
        uuid event_id PK
        string event_code
        string event_name
        string peril
        date start_date
        date end_date
        string region
        string external_event_code
    }
    EVENT_AGGREGATION {
        uuid event_aggregation_id PK
        uuid event_id FK
        uuid section_id FK
        string aggregation_key
        datetime hours_window_start
        datetime hours_window_end
        decimal gross_loss
        decimal ceded_loss_before_limits
        string currency_code
        string status
    }
    CLAIM {
        uuid claim_id PK
        uuid policy_id FK
        uuid location_id FK
        uuid event_id FK
        string claim_number
        date loss_date
        date reported_date
        string cause_of_loss
        string original_currency
        decimal gross_incurred
        decimal gross_paid
        decimal case_reserve
        string status
    }
    CLAIM_TRANSACTION {
        uuid claim_tx_id PK
        uuid claim_id FK
        date transaction_date
        date accounting_period
        string movement_type
        string currency_code
        decimal loss_amount
        decimal expense_amount
        decimal salvage_subrogation_amount
        decimal fx_rate_to_policy
    }
    CLAIM_RESERVE_HISTORY {
        uuid reserve_history_id PK
        uuid claim_id FK
        date valuation_date
        decimal case_indemnity_reserve
        decimal case_expense_reserve
        decimal ceded_case_reserve
        string currency_code
        string reserve_method
    }
    IBNR_ESTIMATE {
        uuid ibnr_estimate_id PK
        uuid program_id FK
        uuid section_id FK
        date valuation_date
        int accident_year
        string method
        decimal gross_ibnr
        decimal ceded_ibnr
        string currency_code
        string model_version
    }
    RECOVERY_ALLOCATION {
        uuid recovery_allocation_id PK
        uuid claim_tx_id FK
        uuid layer_id FK
        uuid participation_id FK
        string calculation_basis
        decimal gross_layer_recovery
        decimal reinsurer_share_pct
        decimal reinsurer_recovery
        string currency_code
        string status
        date recognized_date
        date settled_date
    }
    AGGREGATE_EROSION {
        uuid aggregate_erosion_id PK
        uuid layer_id FK
        uuid claim_tx_id FK
        uuid event_aggregation_id FK
        date valuation_date
        decimal erosion_amount
        decimal cumulative_erosion
        decimal remaining_aggregate_limit
        string currency_code
    }
    REINSTATEMENT {
        uuid reinstatement_id PK
        uuid layer_id FK
        uuid trigger_claim_id FK
        int reinstatement_no
        date triggered_date
        decimal reinstated_limit
        decimal premium_rate_pct
        decimal reinstatement_premium
        string currency_code
        string status
    }
    REINSTATEMENT_EROSION {
        uuid reinstatement_erosion_id PK
        uuid reinstatement_id FK
        uuid claim_tx_id FK
        date erosion_date
        decimal erosion_amount
        decimal cumulative_erosion
        decimal remaining_reinstated_limit
        string currency_code
    }
    TREATY_ACCOUNT {
        uuid treaty_account_id PK
        uuid contract_id FK
        date account_period_start
        date account_period_end
        string account_type
        string currency_code
        decimal premium_amount
        decimal claims_amount
        decimal commission_amount
        decimal brokerage_amount
        decimal tax_amount
        decimal balance_due
        string status
    }
    TREATY_STATEMENT {
        uuid treaty_statement_id PK
        uuid treaty_account_id FK
        uuid participation_id FK
        string statement_number
        date statement_date
        date due_date
        decimal statement_amount
        string currency_code
        string status
    }
    TECHNICAL_ACCOUNTING_ENTRY {
        uuid technical_entry_id PK
        uuid contract_id FK
        uuid section_id FK
        uuid participation_id FK
        string source_type
        string source_reference
        date posting_date
        date accounting_period
        string ledger_account
        decimal debit_amount
        decimal credit_amount
        string currency_code
        string status
    }
    CASH_SETTLEMENT {
        uuid cash_settlement_id PK
        uuid treaty_statement_id FK
        uuid counterparty_id FK
        string settlement_reference
        date value_date
        string direction
        decimal amount
        string currency_code
        string bank_reference
        string status
    }
    COLLATERAL {
        uuid collateral_id PK
        uuid participation_id FK
        string collateral_type
        string provider_name
        string instrument_reference
        date valuation_date
        decimal amount
        string currency_code
        date expiry_date
        string status
    }
    KYC_REVIEW {
        uuid kyc_review_id PK
        uuid counterparty_id FK
        date review_date
        string review_type
        string risk_rating
        boolean beneficial_owner_verified
        boolean source_of_funds_verified
        date next_review_date
        string status
    }
    SANCTIONS_SCREENING {
        uuid sanctions_screening_id PK
        uuid counterparty_id FK
        datetime screened_at
        string provider
        string screening_list_set
        string match_status
        decimal match_score
        string case_reference
        string disposition
    }
    COMMUTATION {
        uuid commutation_id PK
        uuid ceding_entity_id FK
        uuid counterparty_id FK
        string commutation_reference
        date agreement_date
        date effective_date
        decimal settlement_amount
        string currency_code
        string release_scope
        string status
    }
    COMMUTATION_CONTRACT {
        uuid commutation_contract_id PK
        uuid commutation_id FK
        uuid contract_id FK
        decimal allocated_settlement_amount
        string currency_code
    }
    RETROCESSION_PROGRAM {
        uuid retro_program_id PK
        uuid owner_counterparty_id FK
        string retro_program_code
        string program_name
        int underwriting_year
        string currency_code
        string status
    }
    RETROCESSION_CONTRACT {
        uuid retro_contract_id PK
        uuid retro_program_id FK
        uuid source_contract_id FK
        string contract_number
        string contract_type
        date effective_date
        date expiry_date
        string currency_code
        string status
    }
    RETROCESSION_LAYER {
        uuid retro_layer_id PK
        uuid retro_contract_id FK
        uuid source_layer_id FK
        int layer_no
        decimal attachment_point
        decimal layer_limit
        decimal ceded_share_pct
        string currency_code
    }
    RETROCESSION_PARTICIPATION {
        uuid retro_participation_id PK
        uuid retro_layer_id FK
        uuid retrocessionaire_id FK
        decimal signed_share_pct
        decimal brokerage_pct
        string status
    }
    MULTI_CURRENCY_VALUATION {
        uuid valuation_id PK
        date valuation_date
        string object_type
        uuid object_id
        string original_currency
        decimal original_amount
        string functional_currency
        decimal functional_amount
        string reporting_currency
        decimal reporting_amount
        decimal fx_rate_original_to_functional
        decimal fx_rate_functional_to_reporting
        string valuation_basis
    }
    FX_RATE {
        uuid fx_rate_id PK
        date rate_date
        string base_currency
        string quote_currency
        decimal rate
        string rate_type
        string source
    }

    LEGAL_ENTITY ||--o{ REINSURANCE_PROGRAM : owns
    PORTFOLIO_TYPE ||--o{ REINSURANCE_PROGRAM : classifies
    LEGAL_ENTITY ||--o{ UNDERLYING_POLICY : writes
    REINSURANCE_PROGRAM ||--o{ REINSURANCE_CONTRACT : contains
    BROKER o|--o{ REINSURANCE_CONTRACT : intermediates
    REINSURANCE_CONTRACT ||--o{ CONTRACT_VERSION : versions
    CONTRACT_VERSION ||--o{ CONTRACT_WORDING_CLAUSE : contains
    REINSURANCE_CONTRACT ||--o{ CONTRACT_SECTION : contains
    CONTRACT_SECTION ||--o{ REINSURANCE_LAYER : contains
    CONTRACT_SECTION ||--o{ LOSS_CORRIDOR : governs
    CONTRACT_SECTION ||--o{ SLIDING_SCALE_COMMISSION : prices
    REINSURANCE_LAYER ||--o{ LAYER_PARTICIPATION : placed_with
    COUNTERPARTY ||--o{ LAYER_PARTICIPATION : participates
    INSURED ||--o{ UNDERLYING_POLICY : holds
    UNDERLYING_POLICY ||--o{ RISK_LOCATION : contains
    UNDERLYING_POLICY ||--o{ EXPOSURE : contains
    RISK_LOCATION o|--o{ EXPOSURE : locates
    UNDERLYING_POLICY ||--o{ POLICY_SECTION_ALLOCATION : allocated_to
    CONTRACT_SECTION ||--o{ POLICY_SECTION_ALLOCATION : covers
    REINSURANCE_CONTRACT ||--o{ BORDEREAU_BATCH : receives
    BORDEREAU_BATCH o|--o{ PREMIUM_TRANSACTION : imports
    UNDERLYING_POLICY o|--o{ PREMIUM_TRANSACTION : generates
    CONTRACT_SECTION ||--o{ PREMIUM_TRANSACTION : accounts
    REINSURANCE_LAYER o|--o{ PREMIUM_TRANSACTION : prices
    CATASTROPHE_EVENT ||--o{ EVENT_AGGREGATION : grouped_as
    CONTRACT_SECTION ||--o{ EVENT_AGGREGATION : aggregates
    UNDERLYING_POLICY ||--o{ CLAIM : produces
    RISK_LOCATION o|--o{ CLAIM : loss_at
    CATASTROPHE_EVENT o|--o{ CLAIM : causes
    CLAIM ||--o{ CLAIM_TRANSACTION : movements
    CLAIM ||--o{ CLAIM_RESERVE_HISTORY : reserve_snapshots
    REINSURANCE_PROGRAM ||--o{ IBNR_ESTIMATE : estimates
    CONTRACT_SECTION o|--o{ IBNR_ESTIMATE : refines
    CLAIM_TRANSACTION ||--o{ RECOVERY_ALLOCATION : generates
    REINSURANCE_LAYER ||--o{ RECOVERY_ALLOCATION : responds
    LAYER_PARTICIPATION ||--o{ RECOVERY_ALLOCATION : owes
    REINSURANCE_LAYER ||--o{ AGGREGATE_EROSION : erodes
    CLAIM_TRANSACTION o|--o{ AGGREGATE_EROSION : contributes
    EVENT_AGGREGATION o|--o{ AGGREGATE_EROSION : contributes
    REINSURANCE_LAYER ||--o{ REINSTATEMENT : reinstates
    CLAIM ||--o{ REINSTATEMENT : triggers
    REINSTATEMENT ||--o{ REINSTATEMENT_EROSION : erodes
    CLAIM_TRANSACTION ||--o{ REINSTATEMENT_EROSION : consumes
    REINSURANCE_CONTRACT ||--o{ TREATY_ACCOUNT : accounts
    TREATY_ACCOUNT ||--o{ TREATY_STATEMENT : statements
    LAYER_PARTICIPATION o|--o{ TREATY_STATEMENT : addressed_to
    REINSURANCE_CONTRACT ||--o{ TECHNICAL_ACCOUNTING_ENTRY : posts
    CONTRACT_SECTION o|--o{ TECHNICAL_ACCOUNTING_ENTRY : allocates
    LAYER_PARTICIPATION o|--o{ TECHNICAL_ACCOUNTING_ENTRY : allocates
    TREATY_STATEMENT o|--o{ CASH_SETTLEMENT : settles
    COUNTERPARTY ||--o{ CASH_SETTLEMENT : pays_receives
    LAYER_PARTICIPATION ||--o{ COLLATERAL : secured_by
    COUNTERPARTY ||--o{ KYC_REVIEW : reviewed
    COUNTERPARTY ||--o{ SANCTIONS_SCREENING : screened
    LEGAL_ENTITY ||--o{ COMMUTATION : agrees
    COUNTERPARTY ||--o{ COMMUTATION : agrees
    COMMUTATION ||--o{ COMMUTATION_CONTRACT : covers
    REINSURANCE_CONTRACT ||--o{ COMMUTATION_CONTRACT : released
    COUNTERPARTY ||--o{ RETROCESSION_PROGRAM : owns
    RETROCESSION_PROGRAM ||--o{ RETROCESSION_CONTRACT : contains
    REINSURANCE_CONTRACT ||--o{ RETROCESSION_CONTRACT : source_business
    RETROCESSION_CONTRACT ||--o{ RETROCESSION_LAYER : contains
    REINSURANCE_LAYER ||--o{ RETROCESSION_LAYER : source_layer
    RETROCESSION_LAYER ||--o{ RETROCESSION_PARTICIPATION : placed_with
    COUNTERPARTY ||--o{ RETROCESSION_PARTICIPATION : retrocessionaire
```

## Curated mock data

### `legal_entity`

| legal_entity_id | entity_code | entity_name | lei | country_code | base_currency | entity_type | active |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000000101 | AEISE | Alpha Europe Insurance SE | 529900ALPHAEU000001 | DE | EUR | CEDENT | true |

### `counterparty`

| counterparty_id | counterparty_code | counterparty_name | counterparty_type | lei | country_code | rating_agency | financial_rating | collateral_required | active |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000000201 | NORTHSTAR | Northstar Re Ltd | REINSURER | 549300NORTHSTAR0001 | BM | S&P | AA- | false | true |
| 00000000-0000-0000-0000-000000000202 | HELIX | Helix Re AG | REINSURER | 506700HELIXRE000001 | CH | S&P | A+ | false | true |
| 00000000-0000-0000-0000-000000000203 | ATLAS | Atlas Re Bermuda Ltd | REINSURER | 549300ATLASRE000001 | BM | S&P | A | true | true |
| 00000000-0000-0000-0000-000000000204 | BOREAL | Boreal Reinsurance SA | REINSURER | 213800BOREALRE00001 | LU | AM Best | A | false | true |
| 00000000-0000-0000-0000-000000000205 | ORION | Orion Global Re Ltd | REINSURER | 549300ORIONRE000001 | GB | S&P | A- | true | true |
| 00000000-0000-0000-0000-000000000206 | CEDAR | Cedar Retro Partners Ltd | RETROCESSIONAIRE | 549300CEDARRETRO001 | BM | AM Best | A- | true | true |

### `broker`

| broker_id | broker_code | broker_name | country_code | license_reference | contact_email | active |
| --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000000301 | MARINER | Mariner Re Brokers GmbH | DE | DE-RB-44291 | placements@mariner.example | true |
| 00000000-0000-0000-0000-000000000302 | HARBOR | Harbor Re Intermediaries Ltd | GB | UK-RB-91125 | treaty@harbor.example | true |

### `portfolio_type` — 15 portfolio types

| portfolio_type_id | portfolio_type_code | portfolio_type_name | reinsurance_family | default_attachment_basis | default_accounting_basis | description |
| --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000000401 | PROP_CAT_XOL | Property Catastrophe Excess of Loss | NON_PROPORTIONAL | LOSSES_OCCURRING | QUARTERLY | Property catastrophe protection attaching per occurrence with catastrophe event aggregation. |
| 00000000-0000-0000-0000-000000000402 | PROP_PER_RISK_XOL | Property Per Risk Excess of Loss | NON_PROPORTIONAL | LOSSES_OCCURRING | QUARTERLY | Per-risk protection for large commercial property individual risk losses. |
| 00000000-0000-0000-0000-000000000403 | CASUALTY_QS | Casualty Quota Share | PROPORTIONAL | RISKS_ATTACHING | QUARTERLY | Fixed proportional cession of premium and losses for casualty business. |
| 00000000-0000-0000-0000-000000000404 | CASUALTY_SURPLUS | Casualty Surplus Share | PROPORTIONAL | RISKS_ATTACHING | QUARTERLY | Variable proportional cession based on retained lines and insured limits. |
| 00000000-0000-0000-0000-000000000405 | MOTOR_STOP_LOSS | Motor Stop Loss | AGGREGATE_XOL | LOSSES_OCCURRING | ANNUAL | Portfolio aggregate loss-ratio protection for motor insurance. |
| 00000000-0000-0000-0000-000000000406 | MARINE_XOL | Marine Excess of Loss | NON_PROPORTIONAL | LOSSES_OCCURRING | QUARTERLY | Marine hull and cargo occurrence excess of loss protection. |
| 00000000-0000-0000-0000-000000000407 | AVIATION_XOL | Aviation Excess of Loss | NON_PROPORTIONAL | LOSSES_OCCURRING | QUARTERLY | Aviation hull and liability occurrence excess of loss protection. |
| 00000000-0000-0000-0000-000000000408 | CYBER_QS | Cyber Quota Share | PROPORTIONAL | RISKS_ATTACHING | MONTHLY | Proportional cession of cyber risks with accumulation monitoring. |
| 00000000-0000-0000-0000-000000000409 | CYBER_CAT_XOL | Cyber Catastrophe Excess of Loss | NON_PROPORTIONAL | LOSSES_OCCURRING | QUARTERLY | Systemic cyber event protection for correlated cyber losses. |
| 00000000-0000-0000-0000-000000000410 | ENERGY_XOL | Energy Onshore and Offshore Excess of Loss | NON_PROPORTIONAL | LOSSES_OCCURRING | QUARTERLY | Occurrence protection for energy property, business interruption and liability. |
| 00000000-0000-0000-0000-000000000411 | CREDIT_STOP_LOSS | Trade Credit Stop Loss | AGGREGATE_XOL | LOSSES_OCCURRING | QUARTERLY | Annual aggregate protection against elevated credit insurance loss ratios. |
| 00000000-0000-0000-0000-000000000412 | AGRI_MPCX | Agriculture Multi-Peril Crop Excess | AGGREGATE_XOL | LOSSES_OCCURRING | SEASONAL | Seasonal aggregate protection for crop weather and yield losses. |
| 00000000-0000-0000-0000-000000000413 | LIFE_SURPLUS | Life Surplus Reinsurance | PROPORTIONAL | RISKS_ATTACHING | MONTHLY | Surplus cession above cedent retention for mortality risk. |
| 00000000-0000-0000-0000-000000000414 | LIFE_CAT_XOL | Life Catastrophe Excess of Loss | NON_PROPORTIONAL | LOSSES_OCCURRING | QUARTERLY | Catastrophe mortality protection for multiple lives from one event. |
| 00000000-0000-0000-0000-000000000415 | PARAMETRIC_CAT | Parametric Catastrophe Cover | PARAMETRIC | EVENT_OCCURRING | EVENT_BASED | Index-triggered catastrophe reinsurance based on independent event parameters. |

### `reinsurance_program` — one program per portfolio type

| program_id | ceding_entity_id | portfolio_type_id | program_code | program_name | underwriting_year | business_unit | target_currency | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000001401 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000401 | PGM-PROP_CAT_XOL-2026 | Property Catastrophe Excess of Loss 2026 | 2026 | Property Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001402 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000402 | PGM-PROP_PER_RISK_XOL-2026 | Property Per Risk Excess of Loss 2026 | 2026 | Property Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001403 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000403 | PGM-CASUALTY_QS-2026 | Casualty Quota Share 2026 | 2026 | Casualty Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001404 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000404 | PGM-CASUALTY_SURPLUS-2026 | Casualty Surplus Share 2026 | 2026 | Casualty Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001405 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000405 | PGM-MOTOR_STOP_LOSS-2026 | Motor Stop Loss 2026 | 2026 | Motor Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001406 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000406 | PGM-MARINE_XOL-2026 | Marine Excess of Loss 2026 | 2026 | Marine Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001407 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000407 | PGM-AVIATION_XOL-2026 | Aviation Excess of Loss 2026 | 2026 | Aviation Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001408 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000408 | PGM-CYBER_QS-2026 | Cyber Quota Share 2026 | 2026 | Cyber Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001409 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000409 | PGM-CYBER_CAT_XOL-2026 | Cyber Catastrophe Excess of Loss 2026 | 2026 | Cyber Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001410 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000410 | PGM-ENERGY_XOL-2026 | Energy Onshore and Offshore Excess of Loss 2026 | 2026 | Energy Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001411 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000411 | PGM-CREDIT_STOP_LOSS-2026 | Trade Credit Stop Loss 2026 | 2026 | Trade Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001412 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000412 | PGM-AGRI_MPCX-2026 | Agriculture Multi-Peril Crop Excess 2026 | 2026 | Agriculture Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001413 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000413 | PGM-LIFE_SURPLUS-2026 | Life Surplus Reinsurance 2026 | 2026 | Life Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001414 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000414 | PGM-LIFE_CAT_XOL-2026 | Life Catastrophe Excess of Loss 2026 | 2026 | Life Portfolio | EUR | ACTIVE |
| 00000000-0000-0000-0000-000000001415 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000415 | PGM-PARAMETRIC_CAT-2026 | Parametric Catastrophe Cover 2026 | 2026 | Parametric Portfolio | EUR | ACTIVE |

### `reinsurance_contract` — one primary treaty per program

| contract_id | program_id | broker_id | contract_number | contract_name | contract_type | underwriting_year | effective_date | expiry_date | currency_code | attachment_basis | accounting_basis | governing_law | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000001501 | 00000000-0000-0000-0000-000000001401 | 00000000-0000-0000-0000-000000000301 | RE-2026-001 | Property Catastrophe Excess of Loss Contract | CATASTROPHE_XOL | 2026 | 2026-01-01 | 2026-12-31 | EUR | LOSSES_OCCURRING | QUARTERLY | English Law | ACTIVE |
| 00000000-0000-0000-0000-000000001502 | 00000000-0000-0000-0000-000000001402 | 00000000-0000-0000-0000-000000000301 | RE-2026-002 | Property Per Risk Excess of Loss Contract | PER_RISK_XOL | 2026 | 2026-01-01 | 2026-12-31 | EUR | LOSSES_OCCURRING | QUARTERLY | German Law | ACTIVE |
| 00000000-0000-0000-0000-000000001503 | 00000000-0000-0000-0000-000000001403 | 00000000-0000-0000-0000-000000000301 | RE-2026-003 | Casualty Quota Share Contract | QUOTA_SHARE | 2026 | 2026-01-01 | 2026-12-31 | EUR | RISKS_ATTACHING | QUARTERLY | English Law | ACTIVE |
| 00000000-0000-0000-0000-000000001504 | 00000000-0000-0000-0000-000000001404 | 00000000-0000-0000-0000-000000000301 | RE-2026-004 | Casualty Surplus Share Contract | SURPLUS_SHARE | 2026 | 2026-01-01 | 2026-12-31 | EUR | RISKS_ATTACHING | QUARTERLY | German Law | ACTIVE |
| 00000000-0000-0000-0000-000000001505 | 00000000-0000-0000-0000-000000001405 | 00000000-0000-0000-0000-000000000301 | RE-2026-005 | Motor Stop Loss Contract | STOP_LOSS | 2026 | 2026-01-01 | 2026-12-31 | EUR | LOSSES_OCCURRING | ANNUAL | English Law | ACTIVE |
| 00000000-0000-0000-0000-000000001506 | 00000000-0000-0000-0000-000000001406 | 00000000-0000-0000-0000-000000000301 | RE-2026-006 | Marine Excess of Loss Contract | MARINE_XOL | 2026 | 2026-01-01 | 2026-12-31 | EUR | LOSSES_OCCURRING | QUARTERLY | German Law | ACTIVE |
| 00000000-0000-0000-0000-000000001507 | 00000000-0000-0000-0000-000000001407 | 00000000-0000-0000-0000-000000000301 | RE-2026-007 | Aviation Excess of Loss Contract | AVIATION_XOL | 2026 | 2026-01-01 | 2026-12-31 | EUR | LOSSES_OCCURRING | QUARTERLY | English Law | ACTIVE |
| 00000000-0000-0000-0000-000000001508 | 00000000-0000-0000-0000-000000001408 | 00000000-0000-0000-0000-000000000301 | RE-2026-008 | Cyber Quota Share Contract | QUOTA_SHARE | 2026 | 2026-01-01 | 2026-12-31 | EUR | RISKS_ATTACHING | MONTHLY | German Law | ACTIVE |
| 00000000-0000-0000-0000-000000001509 | 00000000-0000-0000-0000-000000001409 | 00000000-0000-0000-0000-000000000301 | RE-2026-009 | Cyber Catastrophe Excess of Loss Contract | CYBER_CAT_XOL | 2026 | 2026-01-01 | 2026-12-31 | EUR | LOSSES_OCCURRING | QUARTERLY | English Law | ACTIVE |
| 00000000-0000-0000-0000-000000001510 | 00000000-0000-0000-0000-000000001410 | 00000000-0000-0000-0000-000000000301 | RE-2026-010 | Energy Onshore and Offshore Excess of Loss Contract | ENERGY_XOL | 2026 | 2026-01-01 | 2026-12-31 | EUR | LOSSES_OCCURRING | QUARTERLY | German Law | ACTIVE |
| 00000000-0000-0000-0000-000000001511 | 00000000-0000-0000-0000-000000001411 | 00000000-0000-0000-0000-000000000301 | RE-2026-011 | Trade Credit Stop Loss Contract | STOP_LOSS | 2026 | 2026-01-01 | 2026-12-31 | EUR | LOSSES_OCCURRING | QUARTERLY | English Law | ACTIVE |
| 00000000-0000-0000-0000-000000001512 | 00000000-0000-0000-0000-000000001412 | 00000000-0000-0000-0000-000000000301 | RE-2026-012 | Agriculture Multi-Peril Crop Excess Contract | AGGREGATE_XOL | 2026 | 2026-01-01 | 2026-12-31 | EUR | LOSSES_OCCURRING | SEASONAL | German Law | ACTIVE |
| 00000000-0000-0000-0000-000000001513 | 00000000-0000-0000-0000-000000001413 | 00000000-0000-0000-0000-000000000301 | RE-2026-013 | Life Surplus Reinsurance Contract | LIFE_SURPLUS | 2026 | 2026-01-01 | 2026-12-31 | EUR | RISKS_ATTACHING | MONTHLY | English Law | ACTIVE |
| 00000000-0000-0000-0000-000000001514 | 00000000-0000-0000-0000-000000001414 | 00000000-0000-0000-0000-000000000301 | RE-2026-014 | Life Catastrophe Excess of Loss Contract | LIFE_CAT_XOL | 2026 | 2026-01-01 | 2026-12-31 | EUR | LOSSES_OCCURRING | QUARTERLY | German Law | ACTIVE |
| 00000000-0000-0000-0000-000000001515 | 00000000-0000-0000-0000-000000001415 | 00000000-0000-0000-0000-000000000301 | RE-2026-015 | Parametric Catastrophe Cover Contract | PARAMETRIC | 2026 | 2026-01-01 | 2026-12-31 | EUR | EVENT_OCCURRING | EVENT_BASED | English Law | ACTIVE |

### `contract_section`

| section_id | contract_id | section_code | section_name | line_of_business | territory_scope | coverage_basis | inuring_priority | hours_clause | annual_aggregate_deductible | annual_aggregate_limit | currency_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000001601 | 00000000-0000-0000-0000-000000001501 | SEC-01 | Property Catastrophe Excess of Loss Main Section | PROPERTY | EU | OCCURRENCE | 1 | 168 | NULL | 150000000 | EUR |
| 00000000-0000-0000-0000-000000001602 | 00000000-0000-0000-0000-000000001502 | SEC-02 | Property Per Risk Excess of Loss Main Section | PROPERTY | EU | OCCURRENCE | 1 | NULL | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001603 | 00000000-0000-0000-0000-000000001503 | SEC-03 | Casualty Quota Share Main Section | GENERAL_LIABILITY | EU | PROPORTIONAL | 1 | NULL | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001604 | 00000000-0000-0000-0000-000000001504 | SEC-04 | Casualty Surplus Share Main Section | GENERAL_LIABILITY | EU | PROPORTIONAL | 1 | NULL | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001605 | 00000000-0000-0000-0000-000000001505 | SEC-05 | Motor Stop Loss Main Section | MOTOR | EU | OCCURRENCE | 1 | NULL | NULL | 50000000 | EUR |
| 00000000-0000-0000-0000-000000001606 | 00000000-0000-0000-0000-000000001506 | SEC-06 | Marine Excess of Loss Main Section | MARINE | WORLDWIDE | OCCURRENCE | 1 | NULL | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001607 | 00000000-0000-0000-0000-000000001507 | SEC-07 | Aviation Excess of Loss Main Section | AVIATION | WORLDWIDE | OCCURRENCE | 1 | NULL | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001608 | 00000000-0000-0000-0000-000000001508 | SEC-08 | Cyber Quota Share Main Section | CYBER | EU | PROPORTIONAL | 1 | NULL | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001609 | 00000000-0000-0000-0000-000000001509 | SEC-09 | Cyber Catastrophe Excess of Loss Main Section | CYBER | EU | OCCURRENCE | 1 | 168 | NULL | 150000000 | EUR |
| 00000000-0000-0000-0000-000000001610 | 00000000-0000-0000-0000-000000001510 | SEC-10 | Energy Onshore and Offshore Excess of Loss Main Section | ENERGY | WORLDWIDE | OCCURRENCE | 1 | NULL | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001611 | 00000000-0000-0000-0000-000000001511 | SEC-11 | Trade Credit Stop Loss Main Section | TRADE_CREDIT | EU | OCCURRENCE | 1 | NULL | NULL | 50000000 | EUR |
| 00000000-0000-0000-0000-000000001612 | 00000000-0000-0000-0000-000000001512 | SEC-12 | Agriculture Multi-Peril Crop Excess Main Section | AGRICULTURE | WORLDWIDE | OCCURRENCE | 1 | NULL | NULL | 50000000 | EUR |
| 00000000-0000-0000-0000-000000001613 | 00000000-0000-0000-0000-000000001513 | SEC-13 | Life Surplus Reinsurance Main Section | LIFE | EU | PROPORTIONAL | 1 | NULL | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001614 | 00000000-0000-0000-0000-000000001514 | SEC-14 | Life Catastrophe Excess of Loss Main Section | LIFE | EU | OCCURRENCE | 1 | 168 | NULL | 150000000 | EUR |
| 00000000-0000-0000-0000-000000001615 | 00000000-0000-0000-0000-000000001515 | SEC-15 | Parametric Catastrophe Cover Main Section | PROPERTY | WORLDWIDE | PARAMETRIC | 1 | NULL | NULL | NULL | EUR |

### `reinsurance_layer`

| layer_id | section_id | layer_no | layer_name | layer_type | attachment_point | layer_limit | annual_aggregate_limit | rate_on_line_pct | minimum_deposit_premium | adjustable_premium_rate_pct | reinstatement_count | reinstatement_rate_pct | currency_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000001701 | 00000000-0000-0000-0000-000000001601 | 1 | EUR 25m xs EUR 25m | OCCURRENCE_XOL | 25000000 | 25000000 | 50000000 | 0.0176 | 440000 | NULL | 1 | 0.5 | EUR |
| 00000000-0000-0000-0000-000000001702 | 00000000-0000-0000-0000-000000001601 | 2 | EUR 50m xs EUR 50m | OCCURRENCE_XOL | 50000000 | 50000000 | 100000000 | 0.0052 | 260000 | NULL | 1 | 1.0 | EUR |
| 00000000-0000-0000-0000-000000001703 | 00000000-0000-0000-0000-000000001602 | 1 | Property Per Risk Excess of Loss Layer 1 | OCCURRENCE_XOL | 14000000 | 26000000 | 52000000 | 0.022 | 572000 | NULL | 1 | 1.0 | EUR |
| 00000000-0000-0000-0000-000000001704 | 00000000-0000-0000-0000-000000001603 | 1 | Casualty Quota Share Layer 1 | PROPORTIONAL | 0 | 23000000 | NULL | NULL | NULL | 0.35 | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001705 | 00000000-0000-0000-0000-000000001604 | 1 | Casualty Surplus Share Layer 1 | PROPORTIONAL | 0 | 24000000 | NULL | NULL | NULL | 0.25 | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001706 | 00000000-0000-0000-0000-000000001605 | 1 | Motor Stop Loss Layer 1 | AGGREGATE_XOL | 20000000 | 40000000 | 40000000 | 0.04 | 1600000 | NULL | 0 | NULL | EUR |
| 00000000-0000-0000-0000-000000001707 | 00000000-0000-0000-0000-000000001606 | 1 | Marine Excess of Loss Layer 1 | OCCURRENCE_XOL | 22000000 | 38000000 | 76000000 | 0.026000000000000002 | 988000 | NULL | 1 | 1.0 | EUR |
| 00000000-0000-0000-0000-000000001708 | 00000000-0000-0000-0000-000000001607 | 1 | Aviation Excess of Loss Layer 1 | OCCURRENCE_XOL | 24000000 | 41000000 | 82000000 | 0.027 | 1107000 | NULL | 1 | 1.0 | EUR |
| 00000000-0000-0000-0000-000000001709 | 00000000-0000-0000-0000-000000001608 | 1 | Cyber Quota Share Layer 1 | PROPORTIONAL | 0 | 28000000 | NULL | NULL | NULL | 0.35 | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001710 | 00000000-0000-0000-0000-000000001609 | 1 | Cyber Catastrophe Excess of Loss Layer 1 | OCCURRENCE_XOL | 28000000 | 47000000 | 94000000 | 0.029 | 1363000 | NULL | 1 | 1.0 | EUR |
| 00000000-0000-0000-0000-000000001711 | 00000000-0000-0000-0000-000000001610 | 1 | Energy Onshore and Offshore Excess of Loss Layer 1 | OCCURRENCE_XOL | 30000000 | 50000000 | 100000000 | 0.03 | 1500000 | NULL | 1 | 1.0 | EUR |
| 00000000-0000-0000-0000-000000001712 | 00000000-0000-0000-0000-000000001611 | 1 | Trade Credit Stop Loss Layer 1 | AGGREGATE_XOL | 26000000 | 52000000 | 52000000 | 0.04 | 2080000 | NULL | 0 | NULL | EUR |
| 00000000-0000-0000-0000-000000001713 | 00000000-0000-0000-0000-000000001612 | 1 | Agriculture Multi-Peril Crop Excess Layer 1 | AGGREGATE_XOL | 27000000 | 54000000 | 54000000 | 0.04 | 2160000 | NULL | 0 | NULL | EUR |
| 00000000-0000-0000-0000-000000001714 | 00000000-0000-0000-0000-000000001613 | 1 | Life Surplus Reinsurance Layer 1 | PROPORTIONAL | 0 | 33000000 | NULL | NULL | NULL | 0.25 | NULL | NULL | EUR |
| 00000000-0000-0000-0000-000000001715 | 00000000-0000-0000-0000-000000001614 | 1 | Life Catastrophe Excess of Loss Layer 1 | OCCURRENCE_XOL | 38000000 | 62000000 | 124000000 | 0.034 | 2108000 | NULL | 1 | 1.0 | EUR |
| 00000000-0000-0000-0000-000000001716 | 00000000-0000-0000-0000-000000001615 | 1 | Parametric Catastrophe Cover Layer 1 | PARAMETRIC | 0 | 40000000 | 40000000 | 0.075 | 3000000 | NULL | 0 | NULL | EUR |

### `layer_participation`

| participation_id | layer_id | reinsurer_id | written_share_pct | signed_share_pct | brokerage_pct | reinsurance_tax_pct | commission_pct | effective_from | effective_to | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000180011 | 00000000-0000-0000-0000-000000001701 | 00000000-0000-0000-0000-000000000201 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180012 | 00000000-0000-0000-0000-000000001701 | 00000000-0000-0000-0000-000000000202 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180021 | 00000000-0000-0000-0000-000000001702 | 00000000-0000-0000-0000-000000000202 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180022 | 00000000-0000-0000-0000-000000001702 | 00000000-0000-0000-0000-000000000203 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180031 | 00000000-0000-0000-0000-000000001703 | 00000000-0000-0000-0000-000000000203 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180032 | 00000000-0000-0000-0000-000000001703 | 00000000-0000-0000-0000-000000000204 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180041 | 00000000-0000-0000-0000-000000001704 | 00000000-0000-0000-0000-000000000204 | 0.65 | 0.6 | 0.05 | 0.0 | 0.27 | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180042 | 00000000-0000-0000-0000-000000001704 | 00000000-0000-0000-0000-000000000205 | 0.45 | 0.4 | 0.05 | 0.0 | 0.27 | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180051 | 00000000-0000-0000-0000-000000001705 | 00000000-0000-0000-0000-000000000205 | 0.65 | 0.6 | 0.05 | 0.0 | 0.27 | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180052 | 00000000-0000-0000-0000-000000001705 | 00000000-0000-0000-0000-000000000201 | 0.45 | 0.4 | 0.05 | 0.0 | 0.27 | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180061 | 00000000-0000-0000-0000-000000001706 | 00000000-0000-0000-0000-000000000201 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180062 | 00000000-0000-0000-0000-000000001706 | 00000000-0000-0000-0000-000000000202 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180071 | 00000000-0000-0000-0000-000000001707 | 00000000-0000-0000-0000-000000000202 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180072 | 00000000-0000-0000-0000-000000001707 | 00000000-0000-0000-0000-000000000203 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180081 | 00000000-0000-0000-0000-000000001708 | 00000000-0000-0000-0000-000000000203 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180082 | 00000000-0000-0000-0000-000000001708 | 00000000-0000-0000-0000-000000000204 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180091 | 00000000-0000-0000-0000-000000001709 | 00000000-0000-0000-0000-000000000204 | 0.65 | 0.6 | 0.05 | 0.0 | 0.27 | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180092 | 00000000-0000-0000-0000-000000001709 | 00000000-0000-0000-0000-000000000205 | 0.45 | 0.4 | 0.05 | 0.0 | 0.27 | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180101 | 00000000-0000-0000-0000-000000001710 | 00000000-0000-0000-0000-000000000205 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180102 | 00000000-0000-0000-0000-000000001710 | 00000000-0000-0000-0000-000000000201 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180111 | 00000000-0000-0000-0000-000000001711 | 00000000-0000-0000-0000-000000000201 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180112 | 00000000-0000-0000-0000-000000001711 | 00000000-0000-0000-0000-000000000202 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180121 | 00000000-0000-0000-0000-000000001712 | 00000000-0000-0000-0000-000000000202 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180122 | 00000000-0000-0000-0000-000000001712 | 00000000-0000-0000-0000-000000000203 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180131 | 00000000-0000-0000-0000-000000001713 | 00000000-0000-0000-0000-000000000203 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180132 | 00000000-0000-0000-0000-000000001713 | 00000000-0000-0000-0000-000000000204 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180141 | 00000000-0000-0000-0000-000000001714 | 00000000-0000-0000-0000-000000000204 | 0.65 | 0.6 | 0.05 | 0.0 | 0.27 | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180142 | 00000000-0000-0000-0000-000000001714 | 00000000-0000-0000-0000-000000000205 | 0.45 | 0.4 | 0.05 | 0.0 | 0.27 | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180151 | 00000000-0000-0000-0000-000000001715 | 00000000-0000-0000-0000-000000000205 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180152 | 00000000-0000-0000-0000-000000001715 | 00000000-0000-0000-0000-000000000201 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180161 | 00000000-0000-0000-0000-000000001716 | 00000000-0000-0000-0000-000000000201 | 0.65 | 0.6 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |
| 00000000-0000-0000-0000-000000180162 | 00000000-0000-0000-0000-000000001716 | 00000000-0000-0000-0000-000000000202 | 0.45 | 0.4 | 0.05 | 0.0 | NULL | 2026-01-01 | NULL | ACTIVE |

### `contract_version`

| contract_version_id | contract_id | version_no | version_status | effective_from | effective_to | signed_date | wording_reference | wording_hash_sha256 | change_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000002001 | 00000000-0000-0000-0000-000000001501 | 1 | SUPERSEDED | 2026-01-01 | 2026-03-31 | 2025-12-20 | PROP-CAT-2026-SLIP-V1 | 6f0f15f6c84a7878429c8924d95df1f680510201d5a5a5d654f121b42608ec41 | Initial signed wording |
| 00000000-0000-0000-0000-000000002002 | 00000000-0000-0000-0000-000000001501 | 2 | CURRENT | 2026-04-01 | NULL | 2026-04-05 | PROP-CAT-2026-SLIP-V2 | 8f14020cab3f4aab8b978963030911d18f9cd14c85793082af9f5d519674fb8d | Clarified flood hours clause and claims cooperation |
| 00000000-0000-0000-0000-000000002003 | 00000000-0000-0000-0000-000000001503 | 1 | CURRENT | 2026-01-01 | NULL | 2025-12-22 | CAS-QS-2026-FINAL | 2f5fb4f62d6598b5553a517b0f97e04d4e7e90158869bfc1ccdd1a24f55c8932 | Final quota-share wording |

### `contract_wording_clause`

| wording_clause_id | contract_version_id | clause_code | clause_title | clause_category | clause_sequence | clause_text | is_manuscript |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000002101 | 00000000-0000-0000-0000-000000002002 | HOURS-FLOOD-168 | Flood 168 Hours Clause | EVENT_DEFINITION | 10 | All flood losses arising during one continuous 168-hour period selected by the cedent are treated as one occurrence. | true |
| 00000000-0000-0000-0000-000000002102 | 00000000-0000-0000-0000-000000002002 | CLAIMS-COOP | Claims Cooperation | CLAIMS | 20 | The cedent shall provide timely notice of material losses and consult the reinsurers on significant settlement strategy. | false |
| 00000000-0000-0000-0000-000000002103 | 00000000-0000-0000-0000-000000002002 | REINSTATEMENT-1 | One Paid Reinstatement | REINSTATEMENT | 30 | One reinstatement of the first layer limit applies at fifty percent additional premium, pro rata as to amount only. | true |
| 00000000-0000-0000-0000-000000002104 | 00000000-0000-0000-0000-000000002003 | QS-35 | Quota Share Percentage | PROPORTIONAL_SHARE | 10 | The cedent cedes and the reinsurers accept thirty-five percent of covered premium and loss. | true |
| 00000000-0000-0000-0000-000000002105 | 00000000-0000-0000-0000-000000002003 | SSC | Sliding Scale Commission | COMMISSION | 20 | Final ceding commission varies with the treaty loss ratio according to the agreed commission table. | true |
| 00000000-0000-0000-0000-000000002106 | 00000000-0000-0000-0000-000000002003 | LOSS-CORRIDOR | Loss Corridor | LOSS_PARTICIPATION | 30 | The cedent retains an additional share of losses within the defined loss-ratio corridor, subject to the annual cap. | true |

### `loss_corridor`

| loss_corridor_id | section_id | corridor_basis | lower_loss_ratio_pct | upper_loss_ratio_pct | cedent_share_pct | reinsurer_share_pct | annual_cap | currency_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000002201 | 00000000-0000-0000-0000-000000001603 | LOSS_RATIO | 0.65 | 0.85 | 0.5 | 0.5 | 5000000 | EUR |
| 00000000-0000-0000-0000-000000002202 | 00000000-0000-0000-0000-000000001605 | LOSS_RATIO | 0.8 | 0.95 | 0.75 | 0.25 | 8000000 | EUR |

### `sliding_scale_commission`

| sliding_scale_id | section_id | loss_ratio_from_pct | loss_ratio_to_pct | commission_pct | provisional_commission_pct | calculation_sequence |
| --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000002301 | 00000000-0000-0000-0000-000000001603 | 0.0 | 0.45 | 0.32 | 0.27 | 1 |
| 00000000-0000-0000-0000-000000002302 | 00000000-0000-0000-0000-000000001603 | 0.450001 | 0.65 | 0.29 | 0.27 | 2 |
| 00000000-0000-0000-0000-000000002303 | 00000000-0000-0000-0000-000000001603 | 0.650001 | 1.0 | 0.24 | 0.27 | 3 |

### `insured`

| insured_id | insured_number | insured_name | industry_code | industry_description | country_code | group_name | active |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000002401 | INS-10001 | Futura Logistics GmbH | 5210 | Warehousing and Logistics | DE | Futura Group | true |
| 00000000-0000-0000-0000-000000002402 | INS-10002 | AlpenTech AG | 2611 | Electronic Manufacturing | AT | AlpenTech Group | true |
| 00000000-0000-0000-0000-000000002403 | INS-10003 | RheinMachinery GmbH | 2829 | Industrial Machinery | DE | NULL | true |
| 00000000-0000-0000-0000-000000002404 | INS-10004 | NordFleet Mobility AG | 4939 | Commercial Motor Fleet | DE | NordFleet Group | true |
| 00000000-0000-0000-0000-000000002405 | INS-10005 | CloudSquare Europe BV | 6201 | Cloud Software | NL | CloudSquare Holdings | true |
| 00000000-0000-0000-0000-000000002406 | INS-10006 | Baltic Energy Services AS | 0910 | Energy Services | NO | Baltic Energy Group | true |

### `underlying_policy`

| policy_id | ceding_entity_id | insured_id | policy_number | line_of_business | inception_date | expiry_date | currency_code | gross_written_premium | sum_insured | policy_limit | deductible | status | metadata_json |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000002501 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000002401 | PROP-DE-260001 | PROPERTY | 2026-01-01 | 2026-12-31 | EUR | 950000 | 120000000 | 100000000 | 5000000 | ACTIVE | {"occupancy":"warehouse","cat_zone":"DE-NORTH"} |
| 00000000-0000-0000-0000-000000002502 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000002402 | PROP-AT-260041 | PROPERTY | 2026-01-01 | 2026-12-31 | EUR | 540000 | 80000000 | 75000000 | 2000000 | ACTIVE | {"occupancy":"electronics","cat_zone":"AT-UPPER"} |
| 00000000-0000-0000-0000-000000002503 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000002403 | GL-DE-260117 | GENERAL_LIABILITY | 2026-01-01 | 2026-12-31 | EUR | 1200000 | NULL | 10000000 | 250000 | ACTIVE | {"products_exposure":true} |
| 00000000-0000-0000-0000-000000002504 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000002404 | MOTOR-DE-260212 | MOTOR | 2026-01-01 | 2026-12-31 | EUR | 2750000 | NULL | 50000000 | 50000 | ACTIVE | {"vehicles":840} |
| 00000000-0000-0000-0000-000000002505 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000002405 | CYBER-NL-260033 | CYBER | 2026-01-01 | 2026-12-31 | USD | 1800000 | NULL | 25000000 | 1000000 | ACTIVE | {"cloud_dependency":"HIGH"} |
| 00000000-0000-0000-0000-000000002506 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000002406 | ENERGY-NO-260071 | ENERGY | 2026-01-01 | 2026-12-31 | NOK | 14500000 | 950000000 | 300000000 | 25000000 | ACTIVE | {"offshore":true} |

### `risk_location`

| location_id | policy_id | location_number | address_line1 | city | postal_code | country_code | latitude | longitude | occupancy_code | construction_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000002601 | 00000000-0000-0000-0000-000000002501 | LOC-001 | Hafenstrasse 88 | Hamburg | 20457 | DE | 53.5358 | 9.9731 | WAREHOUSE | MASONRY |
| 00000000-0000-0000-0000-000000002602 | 00000000-0000-0000-0000-000000002502 | LOC-001 | Industriepark 14 | Linz | 4020 | AT | 48.3002 | 14.2861 | ELECTRONICS_MFG | STEEL_FRAME |
| 00000000-0000-0000-0000-000000002603 | 00000000-0000-0000-0000-000000002503 | LOC-001 | Rheinufer 112 | Koeln | 50668 | DE | 50.9489 | 6.9641 | INDUSTRIAL_OFFICE | CONCRETE |
| 00000000-0000-0000-0000-000000002604 | 00000000-0000-0000-0000-000000002505 | LOC-001 | Science Park 24 | Amsterdam | 1098 XH | NL | 52.3553 | 4.9557 | DATA_CENTER | CONCRETE |
| 00000000-0000-0000-0000-000000002605 | 00000000-0000-0000-0000-000000002506 | LOC-001 | Forusbeen 35 | Stavanger | 4031 | NO | 58.8967 | 5.7315 | ENERGY_SERVICE_BASE | STEEL_FRAME |

### `exposure`

| exposure_id | policy_id | location_id | exposure_type | currency_code | tiv | policy_limit_allocated | deductible_allocated | business_interruption_days | peril_codes_json | as_of_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000002701 | 00000000-0000-0000-0000-000000002501 | 00000000-0000-0000-0000-000000002601 | BUILDING | EUR | 80000000 | 65000000 | 3000000 | NULL | ["FLOOD","FIRE","STORM"] | 2026-01-01 |
| 00000000-0000-0000-0000-000000002702 | 00000000-0000-0000-0000-000000002501 | 00000000-0000-0000-0000-000000002601 | CONTENTS | EUR | 40000000 | 35000000 | 2000000 | NULL | ["FLOOD","FIRE"] | 2026-01-01 |
| 00000000-0000-0000-0000-000000002703 | 00000000-0000-0000-0000-000000002502 | 00000000-0000-0000-0000-000000002602 | BUILDING | EUR | 50000000 | 45000000 | 1200000 | NULL | ["HAIL","FIRE","STORM"] | 2026-01-01 |
| 00000000-0000-0000-0000-000000002704 | 00000000-0000-0000-0000-000000002505 | 00000000-0000-0000-0000-000000002604 | CYBER_DEPENDENCY | USD | NULL | 25000000 | 1000000 | 14 | ["RANSOMWARE","CLOUD_OUTAGE"] | 2026-01-01 |
| 00000000-0000-0000-0000-000000002705 | 00000000-0000-0000-0000-000000002506 | 00000000-0000-0000-0000-000000002605 | OFFSHORE_ENERGY | NOK | 950000000 | 300000000 | 25000000 | 90 | ["FIRE","EXPLOSION","STORM"] | 2026-01-01 |

### `policy_section_allocation`

| allocation_id | policy_id | section_id | ceded_share_pct | subject_premium | subject_sum_insured | effective_from | effective_to |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000002801 | 00000000-0000-0000-0000-000000002501 | 00000000-0000-0000-0000-000000001601 | 1.0 | 950000 | 120000000 | 2026-01-01 | NULL |
| 00000000-0000-0000-0000-000000002802 | 00000000-0000-0000-0000-000000002502 | 00000000-0000-0000-0000-000000001601 | 1.0 | 540000 | 80000000 | 2026-01-01 | NULL |
| 00000000-0000-0000-0000-000000002803 | 00000000-0000-0000-0000-000000002503 | 00000000-0000-0000-0000-000000001603 | 0.35 | 1200000 | 10000000 | 2026-01-01 | NULL |
| 00000000-0000-0000-0000-000000002804 | 00000000-0000-0000-0000-000000002504 | 00000000-0000-0000-0000-000000001605 | 1.0 | 2750000 | 50000000 | 2026-01-01 | NULL |
| 00000000-0000-0000-0000-000000002805 | 00000000-0000-0000-0000-000000002505 | 00000000-0000-0000-0000-000000001608 | 0.35 | 1800000 | 25000000 | 2026-01-01 | NULL |
| 00000000-0000-0000-0000-000000002806 | 00000000-0000-0000-0000-000000002506 | 00000000-0000-0000-0000-000000001610 | 1.0 | 14500000 | 950000000 | 2026-01-01 | NULL |

### `bordereau_batch`

| bordereau_batch_id | contract_id | batch_type | reporting_period_start | reporting_period_end | received_at | source_filename | source_system | record_count | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000002901 | 00000000-0000-0000-0000-000000001501 | PREMIUM | 2026-01-01 | 2026-06-30 | 2026-07-10T09:15:00Z | prop_2026_h1_premium.csv | GUIDEWIRE | 4 | ACCEPTED |
| 00000000-0000-0000-0000-000000002902 | 00000000-0000-0000-0000-000000001501 | CLAIM | 2026-04-01 | 2026-07-31 | 2026-08-08T12:30:00Z | prop_2026_claims_0731.csv | GUIDEWIRE | 2 | ACCEPTED |
| 00000000-0000-0000-0000-000000002903 | 00000000-0000-0000-0000-000000001503 | PREMIUM | 2026-01-01 | 2026-06-30 | 2026-07-11T08:50:00Z | casualty_h1_premium.csv | SAP_FSCD | 1 | ACCEPTED |
| 00000000-0000-0000-0000-000000002904 | 00000000-0000-0000-0000-000000001508 | PREMIUM | 2026-01-01 | 2026-06-30 | 2026-07-12T10:05:00Z | cyber_h1_premium.csv | SNOWFLAKE | 1 | ACCEPTED |

### `premium_transaction`

| premium_tx_id | bordereau_batch_id | policy_id | section_id | layer_id | transaction_type | transaction_date | accounting_period | original_currency | gross_premium | subject_premium | ceded_premium | brokerage_amount | tax_amount | settlement_currency | fx_rate_to_contract |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000003001 | 00000000-0000-0000-0000-000000002901 | 00000000-0000-0000-0000-000000002501 | 00000000-0000-0000-0000-000000001601 | 00000000-0000-0000-0000-000000001701 | WRITTEN | 2026-01-01 | 2026-01-01 | EUR | 950000 | 950000 | 260000 | 13000 | 0 | EUR | 1.0 |
| 00000000-0000-0000-0000-000000003002 | 00000000-0000-0000-0000-000000002901 | 00000000-0000-0000-0000-000000002501 | 00000000-0000-0000-0000-000000001601 | 00000000-0000-0000-0000-000000001702 | WRITTEN | 2026-01-01 | 2026-01-01 | EUR | 950000 | 950000 | 160000 | 8000 | 0 | EUR | 1.0 |
| 00000000-0000-0000-0000-000000003003 | 00000000-0000-0000-0000-000000002901 | 00000000-0000-0000-0000-000000002502 | 00000000-0000-0000-0000-000000001601 | 00000000-0000-0000-0000-000000001701 | WRITTEN | 2026-01-01 | 2026-01-01 | EUR | 540000 | 540000 | 180000 | 9000 | 0 | EUR | 1.0 |
| 00000000-0000-0000-0000-000000003004 | 00000000-0000-0000-0000-000000002903 | 00000000-0000-0000-0000-000000002503 | 00000000-0000-0000-0000-000000001603 | 00000000-0000-0000-0000-000000001704 | WRITTEN | 2026-01-01 | 2026-01-01 | EUR | 1200000 | 1200000 | 420000 | 12600 | 0 | EUR | 1.0 |
| 00000000-0000-0000-0000-000000003005 | 00000000-0000-0000-0000-000000002904 | 00000000-0000-0000-0000-000000002505 | 00000000-0000-0000-0000-000000001608 | 00000000-0000-0000-0000-000000001709 | WRITTEN | 2026-01-01 | 2026-01-01 | USD | 1800000 | 1800000 | 630000 | 18900 | 0 | EUR | 0.92 |

### `catastrophe_event`

| event_id | event_code | event_name | peril | start_date | end_date | region | external_event_code |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000003101 | EVT-DE-FLOOD-2026-01 | Elbe Flood June 2026 | FLOOD | 2026-06-12 | 2026-06-18 | Northern Germany | CAT-EU-26061 |
| 00000000-0000-0000-0000-000000003102 | EVT-AT-HAIL-2026-02 | Upper Austria Hail July 2026 | HAIL | 2026-07-09 | 2026-07-09 | Upper Austria | CAT-EU-26072 |
| 00000000-0000-0000-0000-000000003103 | EVT-CYBER-CLOUD-2026-01 | Pan-European Cloud Service Disruption | CLOUD_OUTAGE | 2026-08-17 | 2026-08-18 | Europe | CYB-260817 |

### `event_aggregation`

| event_aggregation_id | event_id | section_id | aggregation_key | hours_window_start | hours_window_end | gross_loss | ceded_loss_before_limits | currency_code | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000003201 | 00000000-0000-0000-0000-000000003101 | 00000000-0000-0000-0000-000000001601 | PROP-DACH-FLOOD-2026-06-12 | 2026-06-12T00:00:00Z | 2026-06-19T00:00:00Z | 130000000 | 105000000 | EUR | FINAL |
| 00000000-0000-0000-0000-000000003202 | 00000000-0000-0000-0000-000000003102 | 00000000-0000-0000-0000-000000001601 | PROP-DACH-HAIL-2026-07-09 | 2026-07-09T00:00:00Z | 2026-07-16T00:00:00Z | 40000000 | 15000000 | EUR | FINAL |
| 00000000-0000-0000-0000-000000003203 | 00000000-0000-0000-0000-000000003103 | 00000000-0000-0000-0000-000000001609 | CYBER-CAT-2026-08-17 | 2026-08-17T00:00:00Z | 2026-08-24T00:00:00Z | 68000000 | 38000000 | EUR | PRELIMINARY |

### `claim`

| claim_id | policy_id | location_id | event_id | claim_number | loss_date | reported_date | cause_of_loss | original_currency | gross_incurred | gross_paid | case_reserve | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000003301 | 00000000-0000-0000-0000-000000002501 | 00000000-0000-0000-0000-000000002601 | 00000000-0000-0000-0000-000000003101 | CLM-P-260019 | 2026-06-15 | 2026-06-16 | Flood inundation | EUR | 90000000 | 35000000 | 55000000 | OPEN |
| 00000000-0000-0000-0000-000000003302 | 00000000-0000-0000-0000-000000002502 | 00000000-0000-0000-0000-000000002602 | 00000000-0000-0000-0000-000000003102 | CLM-P-260027 | 2026-07-09 | 2026-07-10 | Severe hail | EUR | 40000000 | 10000000 | 30000000 | OPEN |
| 00000000-0000-0000-0000-000000003303 | 00000000-0000-0000-0000-000000002503 | 00000000-0000-0000-0000-000000002603 | NULL | CLM-C-260008 | 2026-04-21 | 2026-04-25 | Product liability | EUR | 6000000 | 1500000 | 4500000 | OPEN |
| 00000000-0000-0000-0000-000000003304 | 00000000-0000-0000-0000-000000002505 | 00000000-0000-0000-0000-000000002604 | 00000000-0000-0000-0000-000000003103 | CLM-Y-260012 | 2026-08-17 | 2026-08-18 | Cloud service interruption | USD | 12000000 | 3000000 | 9000000 | OPEN |

### `claim_transaction`

| claim_tx_id | claim_id | transaction_date | accounting_period | movement_type | currency_code | loss_amount | expense_amount | salvage_subrogation_amount | fx_rate_to_policy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000003401 | 00000000-0000-0000-0000-000000003301 | 2026-06-30 | 2026-06-01 | INCURRED | EUR | 90000000 | 0 | 0 | 1.0 |
| 00000000-0000-0000-0000-000000003402 | 00000000-0000-0000-0000-000000003302 | 2026-07-31 | 2026-07-01 | INCURRED | EUR | 40000000 | 0 | 0 | 1.0 |
| 00000000-0000-0000-0000-000000003403 | 00000000-0000-0000-0000-000000003303 | 2026-06-30 | 2026-06-01 | INCURRED | EUR | 6000000 | 0 | 0 | 1.0 |
| 00000000-0000-0000-0000-000000003404 | 00000000-0000-0000-0000-000000003304 | 2026-08-31 | 2026-08-01 | INCURRED | USD | 12000000 | 0 | 0 | 1.0 |

### `claim_reserve_history`

| reserve_history_id | claim_id | valuation_date | case_indemnity_reserve | case_expense_reserve | ceded_case_reserve | currency_code | reserve_method |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000003501 | 00000000-0000-0000-0000-000000003301 | 2026-06-30 | 55000000 | 2500000 | 40000000 | EUR | CASE_ESTIMATE |
| 00000000-0000-0000-0000-000000003502 | 00000000-0000-0000-0000-000000003301 | 2026-07-31 | 50000000 | 2200000 | 37000000 | EUR | CASE_ESTIMATE |
| 00000000-0000-0000-0000-000000003503 | 00000000-0000-0000-0000-000000003302 | 2026-07-31 | 30000000 | 1000000 | 15000000 | EUR | CASE_ESTIMATE |
| 00000000-0000-0000-0000-000000003504 | 00000000-0000-0000-0000-000000003303 | 2026-06-30 | 4500000 | 500000 | 1575000 | EUR | CASE_ESTIMATE |
| 00000000-0000-0000-0000-000000003505 | 00000000-0000-0000-0000-000000003304 | 2026-08-31 | 9000000 | 750000 | 3150000 | USD | CASE_ESTIMATE |

### `ibnr_estimate`

| ibnr_estimate_id | program_id | section_id | valuation_date | accident_year | method | gross_ibnr | ceded_ibnr | currency_code | model_version |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000003601 | 00000000-0000-0000-0000-000000001401 | 00000000-0000-0000-0000-000000001601 | 2026-06-30 | 2026 | CHAIN_LADDER | 18000000 | 9000000 | EUR | CL-2026Q2-v3 |
| 00000000-0000-0000-0000-000000003602 | 00000000-0000-0000-0000-000000001403 | 00000000-0000-0000-0000-000000001603 | 2026-06-30 | 2026 | BORNHUETTER_FERGUSON | 12500000 | 4375000 | EUR | BF-2026Q2-v2 |
| 00000000-0000-0000-0000-000000003603 | 00000000-0000-0000-0000-000000001405 | 00000000-0000-0000-0000-000000001605 | 2026-06-30 | 2026 | EXPECTED_LOSS_RATIO | 22000000 | 7000000 | EUR | ELR-2026Q2-v1 |
| 00000000-0000-0000-0000-000000003604 | 00000000-0000-0000-0000-000000001408 | 00000000-0000-0000-0000-000000001608 | 2026-06-30 | 2026 | BORNHUETTER_FERGUSON | 9000000 | 3150000 | USD | BF-CYBER-2026Q2-v4 |

### `recovery_allocation`

| recovery_allocation_id | claim_tx_id | layer_id | participation_id | calculation_basis | gross_layer_recovery | reinsurer_share_pct | reinsurer_recovery | currency_code | status | recognized_date | settled_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000003701 | 00000000-0000-0000-0000-000000003401 | 00000000-0000-0000-0000-000000001701 | 00000000-0000-0000-0000-000000180011 | OCCURRENCE_XOL | 25000000 | 0.6 | 15000000 | EUR | RECOGNIZED | 2026-06-30 | NULL |
| 00000000-0000-0000-0000-000000003702 | 00000000-0000-0000-0000-000000003401 | 00000000-0000-0000-0000-000000001701 | 00000000-0000-0000-0000-000000180012 | OCCURRENCE_XOL | 25000000 | 0.4 | 10000000 | EUR | RECOGNIZED | 2026-06-30 | NULL |
| 00000000-0000-0000-0000-000000003703 | 00000000-0000-0000-0000-000000003401 | 00000000-0000-0000-0000-000000001702 | 00000000-0000-0000-0000-000000180021 | OCCURRENCE_XOL | 40000000 | 0.6 | 24000000 | EUR | RECOGNIZED | 2026-06-30 | NULL |
| 00000000-0000-0000-0000-000000003704 | 00000000-0000-0000-0000-000000003401 | 00000000-0000-0000-0000-000000001702 | 00000000-0000-0000-0000-000000180022 | OCCURRENCE_XOL | 40000000 | 0.4 | 16000000 | EUR | RECOGNIZED | 2026-06-30 | NULL |
| 00000000-0000-0000-0000-000000003705 | 00000000-0000-0000-0000-000000003403 | 00000000-0000-0000-0000-000000001704 | 00000000-0000-0000-0000-000000180041 | QUOTA_SHARE | 2100000 | 0.6 | 1260000 | EUR | RECOGNIZED | 2026-06-30 | NULL |
| 00000000-0000-0000-0000-000000003706 | 00000000-0000-0000-0000-000000003403 | 00000000-0000-0000-0000-000000001704 | 00000000-0000-0000-0000-000000180042 | QUOTA_SHARE | 2100000 | 0.4 | 840000 | EUR | RECOGNIZED | 2026-06-30 | NULL |

### `aggregate_erosion`

| aggregate_erosion_id | layer_id | claim_tx_id | event_aggregation_id | valuation_date | erosion_amount | cumulative_erosion | remaining_aggregate_limit | currency_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000003801 | 00000000-0000-0000-0000-000000001701 | 00000000-0000-0000-0000-000000003401 | 00000000-0000-0000-0000-000000003201 | 2026-06-30 | 25000000 | 25000000 | 25000000 | EUR |
| 00000000-0000-0000-0000-000000003802 | 00000000-0000-0000-0000-000000001702 | 00000000-0000-0000-0000-000000003401 | 00000000-0000-0000-0000-000000003201 | 2026-06-30 | 40000000 | 40000000 | 60000000 | EUR |
| 00000000-0000-0000-0000-000000003803 | 00000000-0000-0000-0000-000000001701 | 00000000-0000-0000-0000-000000003402 | 00000000-0000-0000-0000-000000003202 | 2026-07-31 | 15000000 | 40000000 | 10000000 | EUR |

### `reinstatement`

| reinstatement_id | layer_id | trigger_claim_id | reinstatement_no | triggered_date | reinstated_limit | premium_rate_pct | reinstatement_premium | currency_code | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000003901 | 00000000-0000-0000-0000-000000001701 | 00000000-0000-0000-0000-000000003301 | 1 | 2026-06-30 | 25000000 | 0.5 | 220000 | EUR | BOOKED |

### `reinstatement_erosion`

| reinstatement_erosion_id | reinstatement_id | claim_tx_id | erosion_date | erosion_amount | cumulative_erosion | remaining_reinstated_limit | currency_code |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000004001 | 00000000-0000-0000-0000-000000003901 | 00000000-0000-0000-0000-000000003402 | 2026-07-31 | 15000000 | 15000000 | 10000000 | EUR |

### `treaty_account`

| treaty_account_id | contract_id | account_period_start | account_period_end | account_type | currency_code | premium_amount | claims_amount | commission_amount | brokerage_amount | tax_amount | balance_due | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000004101 | 00000000-0000-0000-0000-000000001501 | 2026-01-01 | 2026-06-30 | TECHNICAL | EUR | 600000 | 65000000 | 0 | 30000 | 0 | -64430000 | APPROVED |
| 00000000-0000-0000-0000-000000004102 | 00000000-0000-0000-0000-000000001503 | 2026-01-01 | 2026-06-30 | TECHNICAL | EUR | 420000 | 2100000 | 113400 | 12600 | 0 | -1806000 | APPROVED |
| 00000000-0000-0000-0000-000000004103 | 00000000-0000-0000-0000-000000001508 | 2026-01-01 | 2026-06-30 | TECHNICAL | EUR | 579600 | 0 | 156492 | 17388 | 0 | 405720 | APPROVED |

### `treaty_statement`

| treaty_statement_id | treaty_account_id | participation_id | statement_number | statement_date | due_date | statement_amount | currency_code | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000004201 | 00000000-0000-0000-0000-000000004101 | 00000000-0000-0000-0000-000000180011 | STMT-PROP-2026-H1-NORTHSTAR | 2026-07-15 | 2026-08-14 | -38658000 | EUR | ISSUED |
| 00000000-0000-0000-0000-000000004202 | 00000000-0000-0000-0000-000000004101 | 00000000-0000-0000-0000-000000180012 | STMT-PROP-2026-H1-HELIX | 2026-07-15 | 2026-08-14 | -25772000 | EUR | ISSUED |
| 00000000-0000-0000-0000-000000004203 | 00000000-0000-0000-0000-000000004102 | 00000000-0000-0000-0000-000000180041 | STMT-CAS-2026-H1 | 2026-07-16 | 2026-08-15 | -1083600 | EUR | ISSUED |

### `technical_accounting_entry`

| technical_entry_id | contract_id | section_id | participation_id | source_type | source_reference | posting_date | accounting_period | ledger_account | debit_amount | credit_amount | currency_code | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000004301 | 00000000-0000-0000-0000-000000001501 | 00000000-0000-0000-0000-000000001601 | NULL | PREMIUM | PREM-H1-2026 | 2026-06-30 | 2026-06-01 | CEDED_PREMIUM_RECEIVABLE | 600000 | 0 | EUR | POSTED |
| 00000000-0000-0000-0000-000000004302 | 00000000-0000-0000-0000-000000001501 | 00000000-0000-0000-0000-000000001601 | NULL | CLAIM | CLM-P-260019 | 2026-06-30 | 2026-06-01 | CEDED_CLAIM_RECOVERABLE | 65000000 | 0 | EUR | POSTED |
| 00000000-0000-0000-0000-000000004303 | 00000000-0000-0000-0000-000000001503 | 00000000-0000-0000-0000-000000001603 | NULL | PREMIUM | QS-H1-2026 | 2026-06-30 | 2026-06-01 | CEDED_PREMIUM_PAYABLE | 0 | 420000 | EUR | POSTED |
| 00000000-0000-0000-0000-000000004304 | 00000000-0000-0000-0000-000000001503 | 00000000-0000-0000-0000-000000001603 | NULL | COMMISSION | QS-H1-2026 | 2026-06-30 | 2026-06-01 | CEDING_COMMISSION_RECEIVABLE | 113400 | 0 | EUR | POSTED |
| 00000000-0000-0000-0000-000000004305 | 00000000-0000-0000-0000-000000001501 | 00000000-0000-0000-0000-000000001601 | NULL | REINSTATEMENT | REIN-2026-001 | 2026-06-30 | 2026-06-01 | REINSTATEMENT_PREMIUM_PAYABLE | 0 | 220000 | EUR | POSTED |

### `cash_settlement`

| cash_settlement_id | treaty_statement_id | counterparty_id | settlement_reference | value_date | direction | amount | currency_code | bank_reference | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000004401 | 00000000-0000-0000-0000-000000004201 | 00000000-0000-0000-0000-000000000201 | SET-2026-08-001 | 2026-08-12 | IN | 38658000 | EUR | SWIFT-NSR-884201 | SETTLED |
| 00000000-0000-0000-0000-000000004402 | 00000000-0000-0000-0000-000000004202 | 00000000-0000-0000-0000-000000000202 | SET-2026-08-002 | 2026-08-13 | IN | 25772000 | EUR | SWIFT-HLX-274551 | SETTLED |
| 00000000-0000-0000-0000-000000004403 | 00000000-0000-0000-0000-000000004203 | 00000000-0000-0000-0000-000000000202 | SET-2026-08-003 | 2026-08-14 | IN | 1083600 | EUR | SWIFT-HLX-274997 | SETTLED |

### `collateral`

| collateral_id | participation_id | collateral_type | provider_name | instrument_reference | valuation_date | amount | currency_code | expiry_date | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000004501 | 00000000-0000-0000-0000-000000180022 | LETTER_OF_CREDIT | Atlantic International Bank | LOC-ATLAS-2026-441 | 2026-06-30 | 20000000 | USD | 2027-03-31 | ACTIVE |
| 00000000-0000-0000-0000-000000004502 | 00000000-0000-0000-0000-000000180092 | TRUST_ACCOUNT | European Custody Bank | TRUST-CYBER-2026-33 | 2026-06-30 | 5000000 | EUR | NULL | ACTIVE |

### `kyc_review`

| kyc_review_id | counterparty_id | review_date | review_type | risk_rating | beneficial_owner_verified | source_of_funds_verified | next_review_date | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000004601 | 00000000-0000-0000-0000-000000000201 | 2026-01-05 | ANNUAL | LOW | true | true | 2027-01-05 | APPROVED |
| 00000000-0000-0000-0000-000000004602 | 00000000-0000-0000-0000-000000000203 | 2026-01-07 | ANNUAL | MEDIUM | true | true | 2027-01-07 | APPROVED |
| 00000000-0000-0000-0000-000000004603 | 00000000-0000-0000-0000-000000000206 | 2026-02-01 | ONBOARDING | MEDIUM | true | true | 2027-02-01 | APPROVED |

### `sanctions_screening`

| sanctions_screening_id | counterparty_id | screened_at | provider | screening_list_set | match_status | match_score | case_reference | disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000004701 | 00000000-0000-0000-0000-000000000201 | 2026-08-31T06:00:00Z | WORLD_CHECK | EU,UN,OFAC,UK_HMT | NO_MATCH | 0 | NULL | CLEARED |
| 00000000-0000-0000-0000-000000004702 | 00000000-0000-0000-0000-000000000203 | 2026-08-31T06:02:00Z | WORLD_CHECK | EU,UN,OFAC,UK_HMT | FALSE_POSITIVE | 82.4 | CASE-SANC-2026-188 | CLEARED_AFTER_REVIEW |
| 00000000-0000-0000-0000-000000004703 | 00000000-0000-0000-0000-000000000206 | 2026-08-31T06:04:00Z | WORLD_CHECK | EU,UN,OFAC,UK_HMT | NO_MATCH | 0 | NULL | CLEARED |

### `commutation`

| commutation_id | ceding_entity_id | counterparty_id | commutation_reference | agreement_date | effective_date | settlement_amount | currency_code | release_scope | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000004801 | 00000000-0000-0000-0000-000000000101 | 00000000-0000-0000-0000-000000000205 | COMM-2026-ORION-01 | 2026-05-20 | 2026-06-01 | 4500000 | EUR | Full and final release of all obligations under the specified legacy treaty account balances and outstanding claim recoverables. | EXECUTED |

### `commutation_contract`

| commutation_contract_id | commutation_id | contract_id | allocated_settlement_amount | currency_code |
| --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000004901 | 00000000-0000-0000-0000-000000004801 | 00000000-0000-0000-0000-000000001511 | 4500000 | EUR |

### `retrocession_program`

| retro_program_id | owner_counterparty_id | retro_program_code | program_name | underwriting_year | currency_code | status |
| --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000005001 | 00000000-0000-0000-0000-000000000201 | NSR-RETRO-CAT-2026 | Northstar Property Cat Retrocession 2026 | 2026 | EUR | ACTIVE |

### `retrocession_contract`

| retro_contract_id | retro_program_id | source_contract_id | contract_number | contract_type | effective_date | expiry_date | currency_code | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000005101 | 00000000-0000-0000-0000-000000005001 | 00000000-0000-0000-0000-000000001501 | RETRO-NSR-2026-001 | CAT_XOL | 2026-01-01 | 2026-12-31 | EUR | ACTIVE |

### `retrocession_layer`

| retro_layer_id | retro_contract_id | source_layer_id | layer_no | attachment_point | layer_limit | ceded_share_pct | currency_code |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000005201 | 00000000-0000-0000-0000-000000005101 | 00000000-0000-0000-0000-000000001701 | 1 | 10000000 | 15000000 | 0.5 | EUR |
| 00000000-0000-0000-0000-000000005202 | 00000000-0000-0000-0000-000000005101 | 00000000-0000-0000-0000-000000001702 | 2 | 20000000 | 30000000 | 0.4 | EUR |

### `retrocession_participation`

| retro_participation_id | retro_layer_id | retrocessionaire_id | signed_share_pct | brokerage_pct | status |
| --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000005301 | 00000000-0000-0000-0000-000000005201 | 00000000-0000-0000-0000-000000000206 | 0.7 | 0.05 | ACTIVE |
| 00000000-0000-0000-0000-000000005302 | 00000000-0000-0000-0000-000000005201 | 00000000-0000-0000-0000-000000000204 | 0.3 | 0.05 | ACTIVE |
| 00000000-0000-0000-0000-000000005303 | 00000000-0000-0000-0000-000000005202 | 00000000-0000-0000-0000-000000000206 | 1.0 | 0.05 | ACTIVE |

### `fx_rate`

| fx_rate_id | rate_date | base_currency | quote_currency | rate | rate_type | source |
| --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000005401 | 2026-06-30 | USD | EUR | 0.935 | CLOSING | MOCK_TREASURY |
| 00000000-0000-0000-0000-000000005402 | 2026-06-30 | NOK | EUR | 0.0865 | CLOSING | MOCK_TREASURY |
| 00000000-0000-0000-0000-000000005403 | 2026-06-30 | EUR | USD | 1.06951872 | CLOSING | MOCK_TREASURY |
| 00000000-0000-0000-0000-000000005404 | 2026-08-31 | USD | EUR | 0.92 | CLOSING | MOCK_TREASURY |
| 00000000-0000-0000-0000-000000005405 | 2026-08-31 | EUR | GBP | 0.858 | CLOSING | MOCK_TREASURY |

### `multi_currency_valuation`

| valuation_id | valuation_date | object_type | object_id | original_currency | original_amount | functional_currency | functional_amount | reporting_currency | reporting_amount | fx_rate_original_to_functional | fx_rate_functional_to_reporting | valuation_basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00000000-0000-0000-0000-000000005501 | 2026-06-30 | POLICY | 00000000-0000-0000-0000-000000002505 | USD | 1800000 | EUR | 1683000 | EUR | 1683000 | 0.935 | 1.0 | CLOSING_RATE |
| 00000000-0000-0000-0000-000000005502 | 2026-06-30 | POLICY | 00000000-0000-0000-0000-000000002506 | NOK | 14500000 | EUR | 1254250 | EUR | 1254250 | 0.0865 | 1.0 | CLOSING_RATE |
| 00000000-0000-0000-0000-000000005503 | 2026-06-30 | COLLATERAL | 00000000-0000-0000-0000-000000004501 | USD | 20000000 | EUR | 18700000 | EUR | 18700000 | 0.935 | 1.0 | MARK_TO_MARKET |
| 00000000-0000-0000-0000-000000005504 | 2026-08-31 | CLAIM | 00000000-0000-0000-0000-000000003304 | USD | 12000000 | EUR | 11040000 | EUR | 11040000 | 0.92 | 1.0 | CLOSING_RATE |
| 00000000-0000-0000-0000-000000005505 | 2026-08-31 | IBNR | 00000000-0000-0000-0000-000000003604 | USD | 3150000 | EUR | 2898000 | EUR | 2898000 | 0.92 | 1.0 | CLOSING_RATE |

## Consistency and reconciliation checks

| Check | Expected result |
| --- | --- |
| Number of portfolio types | 15 |
| Property catastrophe layer 1 signed share | 0.60 + 0.40 = 1.00 |
| Property catastrophe layer 2 signed share | 0.60 + 0.40 = 1.00 |
| Casualty quota-share ceded premium | EUR 1,200,000 × 35% = EUR 420,000 |
| Casualty quota-share gross recovery | EUR 6,000,000 × 35% = EUR 2,100,000 |
| Property flood layer 1 recovery | min(max(90,000,000 − 25,000,000, 0), 25,000,000) = EUR 25,000,000 |
| Property flood layer 2 recovery | min(max(90,000,000 − 50,000,000, 0), 50,000,000) = EUR 40,000,000 |
| Property flood total treaty recovery | EUR 65,000,000 |
| Layer 1 paid reinstatement premium | EUR 440,000 × 50% = EUR 220,000 |
| Layer 1 aggregate remaining after flood and hail | EUR 50,000,000 − EUR 25,000,000 − EUR 15,000,000 = EUR 10,000,000 |
| Reinstated limit remaining after hail erosion | EUR 25,000,000 − EUR 15,000,000 = EUR 10,000,000 |
| USD 20,000,000 collateral at 0.935 USD/EUR | EUR 18,700,000 |
| USD 12,000,000 cyber claim at 0.920 USD/EUR | EUR 11,040,000 |

## Recommended database constraints

1. Unique `(program_id, contract_number)` on `reinsurance_contract`.
2. Unique `(contract_id, version_no)` on `contract_version`.
3. Unique `(section_id, layer_no)` on `reinsurance_layer`.
4. Check `signed_share_pct > 0 AND signed_share_pct <= 1`.
5. Validate that active signed shares sum to 1.00 per layer, allowing tolerance for placement rounding where operationally required.
6. Check `attachment_point >= 0`, `layer_limit > 0`, and non-negative financial amounts where negative signs do not encode accounting direction.
7. Unique `(claim_id, valuation_date)` on `claim_reserve_history`.
8. Unique `(program_id, section_id, valuation_date, accident_year, method, model_version)` on `ibnr_estimate`.
9. Check that `hours_window_end > hours_window_start` on `event_aggregation`.
10. Check `cumulative_erosion <= annual_aggregate_limit` where an aggregate limit exists.
11. Check `remaining_reinstated_limit >= 0`.
12. Use explicit debit and credit columns rather than signed amounts in `technical_accounting_entry`.
13. Unique `(rate_date, base_currency, quote_currency, rate_type, source)` on `fx_rate`.
14. Add exclusion or application-level controls preventing overlapping current `contract_version` effective periods.
15. Treat `multi_currency_valuation.object_type + object_id` as a controlled polymorphic reference with validation in application code or database triggers.
