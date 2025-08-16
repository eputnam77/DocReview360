# Standards Mapping

The table below summarizes how DocReview360's verification features align with common compliance standards.

| Implementation Point | Standard Clause | Alignment |
|---------------------|-----------------|----------|
| Certificate validation | FedRAMP SC-23, ISO 27001 A.13.2.1, SOC 2 CC6.1 | TLS certificates are validated and pinned before use to ensure trusted endpoints. |
| Audit logs | FedRAMP AU-2, ISO 27001 A.12.4.1, SOC 2 CC7.2 | Immutable audit logs record verification events and are retained per policy. |
| Role-based access control | FedRAMP AC-2, ISO 27001 A.9.2.3, SOC 2 CC6.2 | Verification data and administrative actions are restricted to authorized roles. |
| Data retention | FedRAMP MP-6, ISO 27001 A.11.2.7, SOC 2 CC3.2 | Automated retention schedules purge logs and archives according to configured limits. |
