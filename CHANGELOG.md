# Changelog

## [0.8.1](https://github.com/dbsanfte/topdesk-mcp/compare/v0.8.0...v0.8.1) (2025-07-02)


### Bug Fixes

* action formatting must be HTML ([f259581](https://github.com/dbsanfte/topdesk-mcp/commit/f259581bdfec7bd611f4d6e8dce208563511f89c))
* MCP exception when calling FunctionTool directly ([3511587](https://github.com/dbsanfte/topdesk-mcp/commit/35115877426e863b4cd0ea35fa642d7d83040bad))

## [0.8.0](https://github.com/dbsanfte/topdesk-mcp/compare/v0.7.0...v0.8.0) (2025-05-29)


### Features

* Markdown conversion for attachments. New 'incident summary' call with all info on the ticket in LLM friendly format. ([56d281e](https://github.com/dbsanfte/topdesk-mcp/commit/56d281e9dcffad11f0b1d80ca6c00afa0a8158f6))


### Bug Fixes

* imports ([34b8b9d](https://github.com/dbsanfte/topdesk-mcp/commit/34b8b9d6079eaf90f0dc573f848b4e26eaa4cb6f))

## [0.7.0](https://github.com/dbsanfte/topdesk-mcp/compare/v0.6.0...v0.7.0) (2025-05-28)


### Features

* include incident attachments as b64_data for ingestion by llm ([668824f](https://github.com/dbsanfte/topdesk-mcp/commit/668824f94536949a8eb9b87b55a2af2e2c3984c3))

## [0.6.0](https://github.com/dbsanfte/topdesk-mcp/compare/v0.5.3...v0.6.0) (2025-05-27)


### Features

* Include inline images in progress trail by default ([003531f](https://github.com/dbsanfte/topdesk-mcp/commit/003531f7d8821b84e5eff4ffbabcbcee29fadd20))

## [0.5.3](https://github.com/dbsanfte/topdesk-mcp/compare/v0.5.2...v0.5.3) (2025-05-23)


### Bug Fixes

* update README with exposed tools, fix hosts in pyproject.toml ([bfd8661](https://github.com/dbsanfte/topdesk-mcp/commit/bfd8661302e8d9bc88f5b4087f480542e496df07))

## [0.5.2](https://github.com/dbsanfte/topdesk-mcp/compare/v0.5.1...v0.5.2) (2025-05-22)


### Bug Fixes

* add attachments flag for progress_trail too, and make these False by default ([5b3ac09](https://github.com/dbsanfte/topdesk-mcp/commit/5b3ac0903b57fa6e53ab47d1baa0a1043b5cf79c))

## [0.5.1](https://github.com/dbsanfte/topdesk-mcp/compare/v0.5.0...v0.5.1) (2025-05-22)


### Bug Fixes

* allow inline attachments for get_incident_actions ([184ff15](https://github.com/dbsanfte/topdesk-mcp/commit/184ff150d7688a8d2d452829fa2db4ab1b96fe30))

## [0.5.0](https://github.com/dbsanfte/topdesk-mcp/compare/0.4.5...v0.5.0) (2025-05-22)


### Features

* prefix mcp tools with `topdesk` to avoid name collisions with other mcp servers ([940ab4c](https://github.com/dbsanfte/topdesk-mcp/commit/940ab4c7b05ff36bdc18bc7187119a028e11cc78))
