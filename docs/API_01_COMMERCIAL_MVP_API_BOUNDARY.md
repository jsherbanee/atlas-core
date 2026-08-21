# API-01 Commercial MVP API Boundary Design

## Purpose

API-01 defines the first request/response boundary for the Commercial MVP.

It gives future Desktop and Web clients stable contracts to call instead of reaching directly into repositories or service internals. This slice is intentionally internal and framework-agnostic: no production web server, no FastAPI routes, and no auth integration.

## Responsibilities

The API boundary translates request DTOs into APP-01 facade calls and converts facade outputs into response envelopes.

It is responsible for:

- explicit tenant context in every request
- deterministic validation errors
- stable request and response contracts for the core Commercial MVP use cases
- tenant isolation across the boundary
- serializable response payloads for future client integration

## Relationship To APP-01

APP-01 is the tenant-scoped Commercial MVP application facade.

API-01 sits on top of that facade and does not reimplement commercial business rules. Its job is to make the APP-01 use cases easier to consume from a product boundary while keeping validation and orchestration deterministic.

## Supported Boundary Use Cases

- create customer/account
- create opportunity
- create estimate
- add, update, and remove estimate line items
- create, mark ready, send, accept, and reject proposals
- convert accepted estimate or proposal into a sales order
- check inventory availability
- reserve inventory
- generate customer invoices from sales orders
- create vendor bills
- mark invoice and vendor bill QuickBooks sync pending
- retrieve a commercial reporting snapshot

## Tenant Isolation

Each request carries tenant context, and the boundary is also bound to a tenant-scoped APP-01 facade.

Cross-tenant requests are rejected deterministically instead of silently touching another tenant's records.

## Out Of Scope

- production web server
- FastAPI or Flask routing
- auth provider integration
- user/session management
- billing
- live QuickBooks API calls
- OAuth
- AWS adapters
- UI implementation
- Epic E

## How This Prepares Future Clients

API-01 is the contract layer future Desktop and Web clients can target first.

It separates client request/response shapes from the underlying commercial services, which makes later delivery surfaces easier to add without reshaping the commercial workflow stack.